"""
This file contains the logic for creating plots with Bokeh. These plots are embedded
into the front end using BokehJS. See Bokeh.tsx for details on how the
front end handles the JSON produced by the Python backend.
"""

import random

import pandas as pd
from bokeh.embed import json_item
from bokeh.layouts import column, row
from bokeh.models import (
    Button,
    CDSView,
    ColumnDataSource,
    CustomJS,
    CustomJSFilter,
    DataTable,
    Div,
    HoverTool,
    MultiSelect,
    TableColumn,
    WheelZoomTool,
)
from bokeh.palettes import Turbo256
from bokeh.plotting import figure
from fastapi import HTTPException


def produce_bokeh_plot(embeddings_df: pd.DataFrame) -> dict:
    """
    Create a Bokeh plot with queries and content points, and a DataTable to display
    selected points, handling duplicate topic titles by using topic_id.
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

    # Combine 'Unknown' topics with 'Unclassified'
    embeddings_df.loc[
        embeddings_df["topic_title"].str.lower() == "unknown",
        ["topic_id", "topic_title"],
    ] = [-1, "Unclassified"]

    # Define special topics
    special_topics = ["Content"]  # 'Content' is the only special topic now
    # can add more if needed

    # Make 'Unclassified' and 'Content' topics semi-transparent
    embeddings_df["alpha"] = embeddings_df["topic_title"].apply(
        lambda t: 0.6 if t.lower() in ["unclassified", "content"] else 1.0
    )

    # Make topics + unclassified gray and everything else blue
    # Blue is just a placeholder - will be overwritten later
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

    # Exclude only 'Content' from topic_counts
    topic_counts = (
        embeddings_df[embeddings_df["topic_title"].str.lower() != "content"]
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

    # Extract topic IDs excluding 'Content'
    unique_topic_ids = sorted_topics["topic_id"].tolist()

    # Separate queries and content
    query_df = embeddings_df[embeddings_df["type"] == "Query"]
    content_df = embeddings_df[embeddings_df["type"] == "Content"]

    # Create ColumnDataSources for queries and content
    source_queries = ColumnDataSource(query_df)
    source_content = ColumnDataSource(content_df)

    # Create MultiSelect widget for topic selection
    multi_select = MultiSelect(
        title="Select Topics:",
        value=[str(tid) for tid in unique_topic_ids],  # All topics selected by default
        options=topic_options,
        size=8,  # Number of visible options (adjust as needed)
        width=500,  # Adjust the width as needed
    )

    # Define CustomJSFilter for filtering based on selected topic_ids
    js_filter = CustomJSFilter(
        args=dict(multi_select=multi_select),
        code="""
        const indices = [];
        const data = source.data;
        const topics = data['topic_id'];
        const selected_topics = multi_select.value.map(Number);

        for (let i = 0; i < topics.length; i++) {
            if (selected_topics.includes(topics[i])) {
                indices.push(true);
            } else {
                indices.push(false);
            }
        }
        return indices;
    """,
    )

    # Create views for queries and content
    view_queries = CDSView(filter=js_filter)
    view_content = CDSView()  # No filter applied to content

    # Attach 'js_on_change' to trigger re-render for queries only
    multi_select.js_on_change(
        "value",
        CustomJS(
            args=dict(source_queries=source_queries),
            code="""
            source_queries.change.emit();
        """,
        ),
    )

    # Create the plot
    plot = figure(
        width=700,
        height=500,
        tools="pan,wheel_zoom,reset,lasso_select",
    )

    wheel_zoom = plot.select_one(WheelZoomTool)
    plot.toolbar.active_scroll = wheel_zoom

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
        nonselection_fill_alpha=0.7,
    )

    # Add content points as hollow squares
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
        nonselection_fill_alpha=0.7,
    )

    # Adjust legend
    plot.legend.location = "top_left"
    plot.legend.click_policy = "hide"

    # Configure hover tool
    hover = HoverTool(
        tooltips=[
            ("Text", "@display_text"),
            ("Topic", "@topic_title"),
        ],
        renderers=[query_renderer, content_renderer],
    )
    plot.add_tools(hover)

    # DataTable to display selected points
    columns = [
        TableColumn(field="display_text", title="Text", width=250),
        TableColumn(field="topic_title", title="Topic", width=210),
    ]
    data_table_source = ColumnDataSource(data=dict(display_text=[], topic_title=[]))

    data_table = DataTable(
        source=data_table_source,
        columns=columns,
        width=500,
        height=200,
        selectable=True,
    )

    # JavaScript code to synchronize selection and update DataTable
    sync_selection_code = """
        const indices_queries = source_queries.selected.indices;
        const indices_content = source_content.selected.indices;

        const d_out = data_table_source.data;
        d_out['display_text'] = [];
        d_out['topic_title'] = [];

        for (let i of indices_queries) {
            d_out['display_text'].push(source_queries.data['display_text'][i]);
            d_out['topic_title'].push(source_queries.data['topic_title'][i]);
        }

        for (let i of indices_content) {
            d_out['display_text'].push(source_content.data['display_text'][i]);
            d_out['topic_title'].push(source_content.data['topic_title'][i]);
        }

        data_table_source.change.emit();
    """

    # Attach callbacks to synchronize selections
    for source in [source_queries, source_content]:
        source.selected.js_on_change(
            "indices",
            CustomJS(
                args=dict(
                    source_queries=source_queries,
                    source_content=source_content,
                    data_table_source=data_table_source,
                ),
                code=sync_selection_code,
            ),
        )

    # Create 'Select All' and 'Deselect All' buttons for topics
    select_all_button = Button(label="Select All", width=80, height=30)
    deselect_all_button = Button(label="Deselect All", width=80, height=30)

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

    # Adjust the layout
    top_layout = row(plot, data_table)
    controls_layout = column(
        Div(text="<b>Topic Selection and Controls:</b>"),
        row(select_all_button, deselect_all_button),
        multi_select,
    )
    layout = column(
        top_layout,
        controls_layout,
    )

    return json_item(layout, "myplot")
