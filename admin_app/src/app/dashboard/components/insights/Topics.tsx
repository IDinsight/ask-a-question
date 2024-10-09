import React, { useEffect } from "react";
import { Box, Typography } from "@mui/material";
import Chip from "@mui/material/Chip";
import ListItemButton from "@mui/material/ListItemButton";
import { orange } from "@mui/material/colors";
import Pagination from "@mui/material/Pagination";
import { useState } from "react";
import { TopicData } from "../../types";

interface TopicProps {
  data?: TopicData[]; // Make data optional
  selectedTopicId: number | null;
  onClick: (topicId: number | null) => void;
  topicsPerPage: number;
}

const Topics: React.FC<TopicProps> = ({
  data = [], // Default to empty array
  selectedTopicId,
  onClick,
  topicsPerPage,
}) => {
  const [page, setPage] = useState(1);
  const [dataToShow, setDataToShow] = useState<TopicData[]>([]);

  const filterPageData = (currentPage: number) => {
    const startIndex = (currentPage - 1) * topicsPerPage;
    const endIndex = startIndex + topicsPerPage;
    setDataToShow(data.slice(startIndex, endIndex));
  };

  useEffect(() => {
    const maxPage = data.length > 0 ? Math.ceil(data.length / topicsPerPage) : 1;

    if (page > maxPage) {
      setPage(maxPage);
      filterPageData(maxPage);
    } else {
      filterPageData(page);
    }
  }, [data]); // Runs when data changes

  useEffect(() => {
    filterPageData(page);
  }, [page]); // Runs when page changes

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        height: "100%",
      }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
        <Typography variant="h6" sx={{ fontWeight: "bold", marginBottom: 1 }}>
          Topics
        </Typography>
        {dataToShow.map((topic) => (
          <Box
            key={topic.topic_id}
            sx={{
              display: "flex",
              bgcolor: selectedTopicId === topic.topic_id ? orange[100] : "white",
              borderRadius: 2,
              fontSize: 14,
            }}
          >
            <Box
              bgcolor={selectedTopicId === topic.topic_id ? orange[500] : "white"}
              sx={{
                minWidth: 6,
                borderTopLeftRadius: 8,
                borderBottomLeftRadius: 8,
              }}
            />
            <ListItemButton
              dense
              onClick={() => onClick(topic.topic_id)}
              sx={{
                display: "flex",
                flexDirection: "row",
                justifyContent: "space-between",
                borderRadius: 2,
                my: 0.5,
                marginLeft: -0.5,
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
      <Box
        justifyContent="center"
        alignItems="flex-end"
        sx={{
          display: "flex",
          mt: 3,
          flexGrow: 0,
        }}
      >
        <Pagination
          defaultPage={1}
          color="primary"
          siblingCount={0}
          page={page}
          onChange={handlePageChange}
          count={data.length > 0 ? Math.ceil(data.length / topicsPerPage) : 1}
        />
      </Box>
    </Box>
  );
};

export default Topics;
