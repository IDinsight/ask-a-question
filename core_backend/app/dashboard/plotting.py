"""
This file contains the logic for creating plots with Bokeh. These plots are embedded
into the front end using BokehJS. See Bokeh.tsx for details on how the
front end handles the JSON produced by the Python backend.
"""

import random

import pandas as pd
from bokeh.core.types import ID
from bokeh.embed import json_item
from bokeh.embed.standalone import StandaloneEmbedJson
from bokeh.layouts import Spacer, column, row
from bokeh.models import (
    Button,
    CDSView,
    ColumnDataSource,
    CustomJS,
    CustomJSFilter,
    Div,
    FixedTicker,
    HoverTool,
    MultiSelect,
    TextInput,
    WheelZoomTool,
)
from bokeh.palettes import Turbo256
from bokeh.plotting import figure
from fastapi import HTTPException


def produce_bokeh_plot(embeddings_df: pd.DataFrame) -> StandaloneEmbedJson:
    """
    Create a Bokeh plot with queries and content points, and a Div to display
    selected points organized by topic, handling duplicate topic
    titles by using topic_id.
    """
    # Ensure required columns are present
    required_columns = ["x", "y", "text", "type", "topic_title", "topic_id"]
    if not all(col in embeddings_df.columns for col in required_columns):
        raise HTTPException(
            status_code=500, detail="Embeddings data missing required columns"
        )

    # Capitalize 'type' column and create 'display_text' column
    embeddings_df["type"] = embeddings_df["type"].str.capitalize()
    embeddings_df["display_text"] = embeddings_df.apply(
        lambda row: (
            row["text"] if row["type"] == "Query" else f"[Content] {row['text']}"
        ),
        axis=1,
    )

    # Ensure 'Content' entries have 'topic_title' == 'Content' and 'topic_id' == -2
    embeddings_df.loc[
        embeddings_df["type"].str.lower() == "content",
        ["topic_id", "topic_title"],
    ] = [-2, "Content"]

    # Combine 'Unknown' topics with 'Unclassified', excluding 'Content' entries
    embeddings_df.loc[
        (embeddings_df["topic_title"].str.lower() == "unknown")
        & (embeddings_df["type"] != "Content"),
        ["topic_id", "topic_title"],
    ] = [-1, "Unclassified"]

    # Define special topics
    special_topics = ["Content"]  # 'Content' is the only special topic now

    # Make 'Unclassified' and 'Content' topics semi-transparent
    embeddings_df["alpha"] = embeddings_df["topic_title"].apply(
        lambda t: 0.6 if t.lower() in ["unclassified", "content"] else 1.0
    )

    # Make 'Unclassified' and 'Content' topics gray, everything else blue
    embeddings_df["color"] = embeddings_df["topic_title"].apply(
        lambda t: ("gray" if t.lower() in ["unclassified", "content"] else "blue")
    )

    # Identify known topics excluding special topics and 'Unclassified' (topic_id == -1)
    known_topics_df = embeddings_df[
        (
            ~embeddings_df["topic_title"]
            .str.lower()
            .isin([t.lower() for t in special_topics])
        )
        & (embeddings_df["topic_id"] != -1)
    ][["topic_title", "topic_id"]].drop_duplicates()

    known_topics = known_topics_df["topic_id"].tolist()

    # Assign colors to known topics
    palette = Turbo256  # Full spectrum color palette
    random.seed(42)  # Set seed for reproducibility between re-rendering plot

    if len(known_topics) <= len(palette):
        topic_colors = random.sample(palette, len(known_topics))
    else:
        # If there are more topics than palette colors, cycle through the palette
        topic_colors = [palette[i % len(palette)] for i in range(len(known_topics))]

    topic_color_map = dict(zip(known_topics, topic_colors))

    # Map colors to embeddings_df based on topic_id, excluding 'Unclassified' (-1)
    embeddings_df.loc[embeddings_df["topic_id"].isin(known_topics), "color"] = (
        embeddings_df["topic_id"].map(topic_color_map)
    )

    # Exclude 'Content' from topic_counts
    topic_counts = (
        embeddings_df[
            ~embeddings_df["topic_title"].str.lower().isin(["content"])
        ]  # type: ignore
        .groupby(["topic_id", "topic_title"])
        .size()
        .reset_index(name="counts")
    )

    # Sort topics by popularity (descending), but place 'Unclassified' at the top
    is_unclassified = topic_counts["topic_title"].str.lower() == "unclassified"
    sorted_topics = pd.concat(
        [
            topic_counts[is_unclassified],
            topic_counts[~is_unclassified].sort_values(by="counts", ascending=False),
        ],
        ignore_index=True,
    )

    # Prepare MultiSelect options and mappings
    topic_options = [
        (str(topic_id), f"{title} ({count})")
        for topic_id, title, count in zip(
            sorted_topics["topic_id"],
            sorted_topics["topic_title"],
            sorted_topics["counts"],
        )
    ]

    # Extract topic IDs, excluding 'Content'
    unique_topic_ids = sorted_topics["topic_id"].tolist()

    # Separate queries and content
    query_df = embeddings_df[embeddings_df["type"] == "Query"]
    content_df = embeddings_df[embeddings_df["type"] == "Content"]

    # Create ColumnDataSources for queries and content
    source_queries = ColumnDataSource(query_df)
    source_content = ColumnDataSource(content_df)

    # Create MultiSelect widget for topic selection
    multi_select = MultiSelect(
        value=[str(tid) for tid in unique_topic_ids],  # All topics selected by default
        options=topic_options,
        width=360,
        height=600,
    )

    # Add TextInput widgets for content and query search
    content_search_input = TextInput(value="", title="Search Content:", width=300)
    query_search_input = TextInput(value="", title="Search Queries:", width=300)

    # Create combined filter for queries
    queries_filter = CustomJSFilter(
        args=dict(multi_select=multi_select, search_input=query_search_input),
        code="""
        const indices = [];
        const data = source.data;
        const topics = data['topic_id'];
        const texts = data['text'];
        const selected_topics = multi_select.value.map(Number);
        const search_value = search_input.value.toLowerCase();

        for (let i = 0; i < topics.length; i++) {
            const topic_id = topics[i];
            const text = texts[i].toLowerCase();
            const text_match = text.includes(search_value);
            const topic_match = selected_topics.includes(topic_id);
            if (topic_match && text_match) {
                indices.push(true);
            } else {
                indices.push(false);
            }
        }
        return indices;
    """,
    )

    # Create modified filter for content to always include 'Content' points
    content_filter = CustomJSFilter(
        args=dict(multi_select=multi_select, search_input=content_search_input),
        code="""
        const indices = [];
        const data = source.data;
        const topics = data['topic_id'];
        const texts = data['text'];
        const search_value = search_input.value.toLowerCase();

        for (let i = 0; i < topics.length; i++) {
            const topic_id = topics[i];
            const text = texts[i].toLowerCase();
            const text_match = text.includes(search_value);
            // Include 'Content' points regardless of topic selection
            if (topic_id === -2 && text_match) {
                indices.push(true);
            } else {
                const selected_topics = multi_select.value.map(Number);
                const topic_match = selected_topics.includes(topic_id);
                if (topic_match && text_match) {
                    indices.push(true);
                } else {
                    indices.push(false);
                }
            }
        }
        return indices;
    """,
    )

    # Create views for queries and content using combined filters
    view_queries = CDSView(filter=queries_filter)
    view_content = CDSView(filter=content_filter)

    # Attach 'js_on_change' to trigger re-render for queries when topic selection or
    # query search input changes
    multi_select.js_on_change(
        "value",
        CustomJS(
            args=dict(source_queries=source_queries, source_content=source_content),
            code="""
            source_queries.change.emit();
            source_content.change.emit();
        """,
        ),
    )

    query_search_input.js_on_change(
        "value",
        CustomJS(
            args=dict(source_queries=source_queries),
            code="""
            source_queries.change.emit();
            """,
        ),
    )

    content_search_input.js_on_change(
        "value",
        CustomJS(
            args=dict(source_content=source_content),
            code="""
            source_content.change.emit();
            """,
        ),
    )

    # Create the plot
    plot = figure(
        tools="pan,wheel_zoom,reset,lasso_select",
        height=610,
        width=750,
    )

    # Set the wheel zoom tool as the active scroll tool
    wheel_zoom = plot.select_one({"type": WheelZoomTool})
    plot.toolbar.active_scroll = wheel_zoom

    # Adjust plot appearance
    plot.xaxis.visible = False  # Remove x-axis numbers
    plot.yaxis.visible = False  # Remove y-axis numbers
    plot.xgrid.grid_line_color = "lightgray"  # Keep x-grid lines visible
    plot.ygrid.grid_line_color = "lightgray"  # Keep y-grid lines visible

    # Add more frequent ticks every 3 units
    plot.xaxis.ticker = FixedTicker(ticks=[i for i in range(-100, 101, 3)])
    plot.yaxis.ticker = FixedTicker(ticks=[i for i in range(-100, 101, 3)])

    # Add query points as circles
    query_renderer = plot.circle(
        "x",
        "y",
        size=6,
        color="color",
        source=source_queries,
        view=view_queries,
        legend_label="Queries",
        alpha="alpha",
        selection_line_color="black",
        selection_line_width=2,
        nonselection_alpha=0.3,  # Set non-selected points alpha to 0.3
    )

    # Add content points as hollow squares with updated view_content
    content_renderer = plot.square(
        "x",
        "y",
        size=13,
        line_color="black",
        fill_alpha=0,
        color="color",
        source=source_content,
        view=view_content,
        legend_label="Content",
        alpha="alpha",
        selection_line_color="black",
        selection_line_width=2,
        nonselection_alpha=0.3,  # Set non-selected points alpha to 0.3
    )

    # Adjust legend
    plot.legend.location = "top_left"
    plot.legend.click_policy = "hide"

    # Configure hover tool with styling to wrap long text
    hover = HoverTool(
        tooltips="""
        <div style="width:300px; white-space: normal;">
            <b>Text:</b> @display_text <br>
            <b>Topic:</b> @topic_title
        </div>
        """,
        renderers=[query_renderer, content_renderer],
    )
    plot.add_tools(hover)

    # Create a Div to display aggregated selected points organized by topic
    div = Div(
        styles={"white-space": "pre-wrap", "overflow-y": "auto"},
        sizing_mode="stretch_width",
        height=350,  # Reduced height by ~30%
    )

    # JavaScript code to synchronize selection and update Div
    sync_selection_code = """
        const indices_queries = source_queries.selected.indices;
        const indices_content = source_content.selected.indices;

        const data_queries = source_queries.data;
        const data_content = source_content.data;

        // Aggregate selected points by topic
        let topics = {};
        // Process selected queries
        for (let i of indices_queries) {
            const topic = data_queries['topic_title'][i];
            const query = data_queries['display_text'][i];
            if (!(topic in topics)) {
                topics[topic] = [];
            }
            topics[topic].push(query);
        }
        // Process selected content
        for (let i of indices_content) {
            const topic = data_content['topic_title'][i];
            const query = data_content['display_text'][i];
            if (!(topic in topics)) {
                topics[topic] = [];
            }
            topics[topic].push(query);
        }
        // Build HTML content
        let content = "";
        for (let topic in topics) {
            content += "<b>" + topic + "</b><br>";
            for (let q of topics[topic]) {
                content += q + "<br>";
            }
            content += "<br>";
        }
        div.text = content;
    """

    # Attach callbacks to synchronize selections
    sync_selection_callback = CustomJS(
        args=dict(
            source_queries=source_queries,
            source_content=source_content,
            div=div,
        ),
        code=sync_selection_code,
    )

    for source in [source_queries, source_content]:
        source.selected.js_on_change(
            "indices",
            sync_selection_callback,
        )

    # Create 'Select All' and 'Deselect All' buttons for topics
    select_all_button = Button(label="Select All", width=100, height=30)
    deselect_all_button = Button(label="Deselect All", width=100, height=30)

    # JavaScript callbacks for the buttons
    select_all_callback = CustomJS(
        args=dict(multi_select=multi_select),
        code=f"""
        multi_select.value = { [str(tid) for tid in unique_topic_ids] };
        multi_select.change.emit();
    """,
    )
    select_all_button.js_on_click(select_all_callback)

    deselect_all_callback = CustomJS(
        args=dict(multi_select=multi_select),
        code="""
        multi_select.value = [];
        multi_select.change.emit();
    """,
    )
    deselect_all_button.js_on_click(deselect_all_callback)

    # Create the left column: Buttons and Scrollable topics
    left_column = column(
        Div(text="<b>Topics:</b>", margin=(0, 0, 0, 0)),
        row(select_all_button, deselect_all_button, sizing_mode="fixed"),
        Spacer(height=13),  # Padding so that layout looks neatest
        multi_select,
    )

    # Create the search bars row
    search_bars = column(
        row(
            content_search_input,
            Spacer(width=104),  # For padding purposes again
            query_search_input,
            sizing_mode="stretch_width",
            margin=(0, 0, 11, 0),
        ),
    )

    # Create the right column: Search bars and plot
    right_column = column(
        search_bars,
        plot,
    )

    # Combine the left and right columns into the top layout
    top_layout = row(
        left_column,
        right_column,
        sizing_mode="stretch_width",
    )

    # Create the data table (Div) with full width below the top layout
    div_layout = column(
        Div(
            text="<h4>Selected points (use the lasso tool to populate this table)</h4>",
            styles={"text-align": "center"},
        ),
        div,
        sizing_mode="stretch_width",
    )

    # Create the overall layout
    layout = column(
        top_layout,
        div_layout,
        sizing_mode="stretch_width",
    )

    return json_item(layout, ID("myplot"))
