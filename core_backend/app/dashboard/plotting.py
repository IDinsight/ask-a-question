"""
This file contains the logic for creating plots with Bokeh. These plots are embedded
into the front end using BokehJS. See Bokeh.tsx for details on how the
front end handles the json produced by Python backend
"""

import random

import pandas as pd
from bokeh.embed import json_item
from bokeh.layouts import column, row
from bokeh.models import (
    CheckboxGroup,
    ColumnDataSource,
    CustomJS,
    DataTable,
    HoverTool,
    TableColumn,
    WheelZoomTool,
)
from bokeh.palettes import Turbo256
from bokeh.plotting import figure
from fastapi import HTTPException


def produce_bokeh_plot(embeddings_df: pd.DataFrame) -> dict:
    """
    Create a Bokeh plot with queries and content points, and a DataTable to display
    selected points.
    """
    # Ensure required columns are present
    required_columns = ["x", "y", "text", "type", "topic_title"]
    if not all(col in embeddings_df.columns for col in required_columns):
        raise HTTPException(
            status_code=500, detail="Embeddings data missing required columns"
        )

    # Capitalize 'type' column and create separate 'display_text' column
    # for displaying text in the plot and DataTable
    embeddings_df["type"] = embeddings_df["type"].str.capitalize()
    embeddings_df["display_text"] = embeddings_df.apply(
        lambda row: (
            row["text"] if row["type"] == "Query" else f"[Content] {row['text']}"
        ),
        axis=1,
    )

    # Make 'Unknown' and 'Unclassified' topics semi-transparent
    unknown_topics = ["Unknown", "Unclassified"]
    embeddings_df["alpha"] = embeddings_df["topic_title"].apply(
        lambda t: 0.6 if t.lower() in [ut.lower() for ut in unknown_topics] else 1.0
    )

    # Assign 'grey' color to 'Unknown' or 'Unclassified' topics
    embeddings_df["color"] = "grey"  # Default color for all

    # Identify known topics
    known_topics = embeddings_df[
        ~embeddings_df["topic_title"]
        .str.lower()
        .isin([t.lower() for t in unknown_topics])
    ]["topic_title"].unique()

    # Randomly assign colors to known topics
    palette = Turbo256  # Full spectrum color palette
    random.seed(42)  # Set seed for reproducibility between refreshes
    topic_colors = random.sample(palette, len(known_topics))
    topic_color_map = dict(zip(known_topics, topic_colors))

    # Map colors to embeddings_df
    embeddings_df.loc[embeddings_df["topic_title"].isin(known_topics), "color"] = (
        embeddings_df["topic_title"].map(topic_color_map)
    )

    # Filter queries
    query_df = embeddings_df[embeddings_df["type"] == "Query"]
    # Filter contents
    content_df = embeddings_df[embeddings_df["type"] == "Content"]

    # Create ColumnDataSource for queries
    source_queries = ColumnDataSource(
        data=dict(
            x=query_df["x"],
            y=query_df["y"],
            color=query_df["color"],
            display_text=query_df["display_text"].tolist(),
            topic_title=query_df["topic_title"].tolist(),
            alpha=query_df["alpha"].tolist(),
        )
    )

    # Create ColumnDataSource for content
    source_content = ColumnDataSource(
        data=dict(
            x=content_df["x"],
            y=content_df["y"],
            color=content_df["color"],
            display_text=content_df["display_text"].tolist(),
            topic_title=content_df["topic_title"].tolist(),
            alpha=content_df["alpha"].tolist(),
        )
    )

    # Create a figure with pan, wheel_zoom, reset, and lasso_select tools
    plot = figure(
        width=700,
        height=500,
        tools="pan,wheel_zoom,reset,lasso_select",
    )

    wheel_zoom = plot.select_one(WheelZoomTool)
    plot.toolbar.active_scroll = wheel_zoom

    # Add query points as circles with size units in data coordinates
    query_renderer = plot.circle(
        "x",
        "y",
        size=6,  # Can tweak if data min/max changes
        color="color",
        source=source_queries,
        legend_label="Queries",
        alpha="alpha",
        selection_line_color="black",
        nonselection_fill_alpha=0.7,
    )

    # Add content points as empty black squares with size units in data coordinates,
    # initially invisible
    content_renderer = plot.square(
        "x",
        "y",
        size=13,
        line_color="black",
        fill_alpha=0,
        alpha="alpha",
        source=source_content,
        visible=False,
        legend_label="Content",
        selection_line_color="black",
        nonselection_fill_alpha=0.7,
    )

    # Adjust legend + add ability to hide content/ query points
    plot.legend.location = "top_left"
    plot.legend.click_policy = "hide"

    # Checkbox group to toggle content points visibility to replicate the
    # functionality of the legend but slightly more obviously for users
    checkbox = CheckboxGroup(labels=["Also show content cards"])
    # Callback to toggle the visibility of content points
    checkbox_callback = CustomJS(
        args=dict(content_renderer=content_renderer),
        code="""
        content_renderer.visible = cb_obj.active.includes(0);
    """,
    )

    # Attach the callback to the checkbox group
    checkbox.js_on_change("active", checkbox_callback)

    # Add hover tool to display text and cluster information
    # Pull data from the newly created display_text and topic_title columns
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

    # CReate DataTable from source
    data_table = DataTable(
        source=data_table_source,
        columns=columns,
        width=500,
        height=500,
        selectable=True,
    )

    # JavaScript code to synchronize selection and update DataTable
    # Allows for selection of points -> DataTable updates live with selected points
    sync_selection_code = """
        // Synchronize selections between query and content sources
        const indices = [];
        for (let i = 0; i < source_queries.selected.indices.length; i++) {
            indices.push(source_queries.selected.indices[i]);
        }
        for (let i = 0; i < source_content.selected.indices.length; i++) {
            indices.push(source_content.selected.indices[i]);
        }

        // Update DataTable
        const d_out = data_table_source.data;
        d_out['display_text'] = [];
        d_out['topic_title'] = [];

        // Add selected query data
        for (let i of source_queries.selected.indices) {
            d_out['display_text'].push(source_queries.data['display_text'][i]);
            d_out['topic_title'].push(source_queries.data['topic_title'][i]);
        }
        // Add selected content data
        for (let i of source_content.selected.indices) {
            d_out['display_text'].push(source_content.data['display_text'][i]);
            d_out['topic_title'].push(source_content.data['topic_title'][i]);
        }
        data_table_source.change.emit();
    """

    # Attach callbacks to synchronize selections
    source_queries.selected.js_on_change(
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

    source_content.selected.js_on_change(
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

    # Ensure that selection tools affect both data sources
    plot.renderers.extend([query_renderer, content_renderer])

    # Move checkbox to the top of the layout
    layout = column(checkbox, row(plot, data_table))

    return json_item(layout, "myplot")
