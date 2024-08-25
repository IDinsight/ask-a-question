import React, { useState, useEffect } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Pagination from "@mui/material/Pagination";
import Chip from "@mui/material/Chip";
import { useAuth } from "@/utils/auth";
import { fetchTopicsData } from "@/app/dashboard/api";

// Interfaces
interface Topic {
  name: string;
  examples: { timestamp: string; userQuestion: string }[];
  topic_popularity: string;
}

const TopicsSection: React.FC = () => {
  const { token } = useAuth();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [n_topics, setNTopics] = useState<number>(0);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isInitialLoad, setIsInitialLoad] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const topicsPerPage = 5;

  useEffect(() => {
    /// check for token first
    if (!token) {
      return;
    }
    const initDataFetch = async () => {
      setLoading(true);
      try {
        const data = await fetchTopicsData(token);

        const fetchedTopics = data.topics.map((topic: any) => ({
          name: topic.topic_name, // Make sure the keys match the response of the API
          topic_popularity: topic.topic_popularity,
          examples: topic.topic_samples.map((sample: string) => ({
            timestamp: "2024-07-23 06:01PM", // Adjust this accordingly if there's a timestamp in the API
            userQuestion: sample,
          })),
        }));

        setTopics(fetchedTopics);
        setNTopics(data.n_topics);
      } catch (err) {
        console.error("Error fetching topics:", err);
        setError("Failed to load topics");
      } finally {
        setLoading(false);
      }
    };

    if (isInitialLoad) {
      initDataFetch().then(() => setIsInitialLoad(false));
    }
  }, [token, isInitialLoad]); // Only re-run the effect if token changes

  const handlePageChange = (
    _event: React.ChangeEvent<unknown>,
    value: number,
  ) => {
    setCurrentPage(value);
  };

  // Render the loading spinner only during the initial load
  if (loading && isInitialLoad) {
    return (
      <Container>
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="50vh"
          flexDirection="column"
        >
          <CircularProgress size={60} />
          <Typography variant="subtitle1" marginTop={2}>
            Generating insights...
          </Typography>
        </Box>
      </Container>
    );
  }

  // If there is an error, display it
  if (error) {
    return (
      <Typography variant="h6" color="error">
        {error}
      </Typography>
    );
  }

  const selectTopic = (topic: Topic) => {
    setSelectedTopic(topic);
  };

  // Determine the topics to display based on the current page
  const currentTopics = topics.slice(
    (currentPage - 1) * topicsPerPage,
    currentPage * topicsPerPage,
  );

  return (
    <Box
      sx={{
        boxShadow: 2,
        borderRadius: 2,
        p: 2,
        width: "100%",
        bgcolor: "#fff",
      }}
    >
      <List>
        {currentTopics.map((topic, index) => (
          <ListItem
            button
            key={index}
            selected={selectedTopic === topic}
            onClick={() => selectTopic(topic)}
          >
            <ListItemText primary={topic.name} />
            <Chip label={topic.topic_popularity} color="primary" />
          </ListItem>
        ))}
      </List>
      <Pagination
        count={Math.ceil(n_topics / topicsPerPage)}
        page={currentPage}
        onChange={handlePageChange}
        color="primary"
        sx={{ display: "flex", justifyContent: "center", p: 3 }}
      />
      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", p: 2 }}>
          <CircularProgress size={24} />
        </Box>
      ) : null}
      <TableContainer component={Box}>
        <Table aria-label="example sentences" size="small">
          <TableHead>
            <TableRow>
              <TableCell
                sx={{
                  width: 200,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                Timestamp
              </TableCell>
              <TableCell sx={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                User Question
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {selectedTopic?.examples.map((example, index) => (
              <TableRow key={index}>
                <TableCell
                  sx={{ overflow: "hidden", textOverflow: "ellipsis" }}
                >
                  {example.timestamp}
                </TableCell>
                <TableCell
                  sx={{ overflow: "hidden", textOverflow: "ellipsis" }}
                >
                  {example.userQuestion}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default TopicsSection;
