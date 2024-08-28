import React from "react";
import { Box } from "@mui/material";
import Chip from "@mui/material/Chip";
import ListItemButton from "@mui/material/ListItemButton";
import { useState } from "react";
import { orange } from "@mui/material/colors";

interface TopicData {
  topic: string;
  count: number;
}

interface TopicProps {
  data: TopicData[];
}

const Topics: React.FC<TopicProps> = ({ data }) => {
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);

  return (
    <Box sx={{ display: "flex", flexDirection: "column" }}>
      <Box sx={{ mb: 1, fontSize: 22, fontWeight: 700 }}>Topics</Box>
      {data.map((topic) => (
        <Box
          sx={{
            display: "flex",
            bgcolor: selectedTopic == topic.topic ? orange[100] : "white",
            borderRadius: 2,
            fontSize: 14,
          }}
        >
          <Box
            bgcolor={selectedTopic == topic.topic ? orange[500] : "white"}
            sx={{
              minWidth: 6,
              borderTopLeftRadius: 8,
              borderBottomLeftRadius: 8,
            }}
          />
          <ListItemButton
            key={topic.topic}
            dense={true}
            onClick={() => setSelectedTopic(topic.topic)}
            sx={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "space-between",
              borderRadius: 2,
              my: 0.5,
              ml: -0.5,
            }}
          >
            <Box>{topic.topic}</Box>
            <Box>
              <Chip label={topic.count} variant="filled" size="small" />
            </Box>
          </ListItemButton>
        </Box>
      ))}
    </Box>
  );
};

export default Topics;
