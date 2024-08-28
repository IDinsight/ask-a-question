import React from "react";
import { Box } from "@mui/material";
import Chip from "@mui/material/Chip";
import ListItemButton from "@mui/material/ListItemButton";
import { orange } from "@mui/material/colors";
import { TopicData } from "../../types";

interface TopicProps {
  data: TopicData[];
  selectedTopicId: number | null;
  onClick: (topic: number | null) => void;
}

const Topics: React.FC<TopicProps> = ({ data, selectedTopicId, onClick }) => {
  return (
    <Box sx={{ display: "flex", flexDirection: "column" }}>
      <Box sx={{ mb: 1, fontSize: 22, fontWeight: 700 }}>Topics</Box>
      {data.map((topic) => (
        <Box
          key={topic.topic_id}
          sx={{
            display: "flex",
            bgcolor: selectedTopicId == topic.topic_id ? orange[100] : "white",
            borderRadius: 2,
            fontSize: 14,
          }}
        >
          <Box
            bgcolor={selectedTopicId == topic.topic_id ? orange[500] : "white"}
            sx={{
              minWidth: 6,
              borderTopLeftRadius: 8,
              borderBottomLeftRadius: 8,
            }}
          />
          <ListItemButton
            key={topic.topic_id}
            dense={true}
            onClick={() => onClick(topic.topic_id)}
            sx={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "space-between",
              borderRadius: 2,
              my: 0.5,
              ml: -0.5,
            }}
          >
            <Box>{topic.topic_name}</Box>
            <Box>
              <Chip label={topic.topic_popularity} variant="filled" size="small" />
            </Box>
          </ListItemButton>
        </Box>
      ))}
    </Box>
  );
};

export default Topics;
