import React, { useState, useEffect, useRef } from "react";
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
import { fetchTopicsData, generateNewTopics } from "@/app/dashboard/api";
import { Period } from "@/app/dashboard/types";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import Button from "@mui/material/Button";
import { format } from "date-fns";

// Interfaces
interface Topic {
  name: string;
  examples: { timestamp: string; userQuestion: string }[];
  topic_popularity: string;
}

interface InsightsProps {
  timePeriod: Period;
}

const Insights: React.FC<InsightsProps> = ({ timePeriod }) => {
  const { token } = useAuth();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [n_topics, setNTopics] = useState<number>(0);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const topicsPerPage = 5;
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [showPopup, setShowPopup] = useState(false);
  const prevTimePeriod = useRef<string | null>(null);
  const [lastGeneratedTimestamp, setLastGeneratedTimestamp] = useState<string | null>(
    null,
  );

  useEffect(() => {
    const fetchData = async () => {
      if (token && timePeriod) {
        setFetching(true);
        setError(null); // Clear any previous errors
        try {
          const data = await fetchTopicsData(timePeriod, token);
          const fetchedTopics = data.topics
            .map((topic) => ({
              name: topic.topic_name,
              topic_popularity: topic.topic_popularity,
              examples: topic.topic_samples.map((sample) => ({
                userQuestion: sample[0],
                timestamp: sample[1],
              })),
            }))
            .sort((a, b) => b.topic_popularity - a.topic_popularity);

          setShowPopup(fetchedTopics.length === 0); // Show the popup if there are no topics

          if (fetchedTopics.length === 0 || timePeriod !== prevTimePeriod.current) {
            setSelectedTopic(null); // Reset selected topic if the time period has changed or there are no topics
          }

          setTopics(fetchedTopics);
          setNTopics(data.n_topics);
        } catch (error) {
          setError(error); // Set error state
          setShowPopup(false); // Ensure popup doesn't show if there's an error
        } finally {
          setFetching(false); // Hide spinner after fetch attempt
        }
      }
    };

    fetchData(); // Call the fetchData function
    prevTimePeriod.current = timePeriod; // Update the previous time period after the fetch logic runs
  }, [token, timePeriod]); // Effect runs when token or timePeriod changes

  useEffect(() => {
    prevTimePeriod.current = timePeriod;
  }, [timePeriod]);

  const selectTopic = (topic: Topic) => {
    setSelectedTopic(topic);
  };

  // Add this inside the useEffect hook or where you handle the topics fetching

  const currentTopics = topics.slice(
    (currentPage - 1) * topicsPerPage,
    currentPage * topicsPerPage,
  );

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setCurrentPage(value);
  };

  const generateInsightsDummy = () => {
    const currentTime = new Date();
    setLastGeneratedTimestamp(format(currentTime, "PPpp")); // Formats the current time to a readable string
    console.log("Generating new topic insights...");
    // Further logic will go here when the function is fully implemented.
  };

  const handleGenerateNewTopics = async () => {
    if (!token) {
      setError(new Error("No authentication token available."));
      return;
    }
    setShowPopup(false); // Close the popup dialog
    setFetching(true); // Start the spinning wheel
    try {
      // Trigger the backend process; we don't care about the response body if it's just a 200
      await generateNewTopics(timePeriod, token);
      // Now poll the server to check if the new topics have been generated
      const newTopicsData = await fetchTopicsData(timePeriod, token);
      setTopics(newTopicsData.topics || []);
      setNTopics(newTopicsData.n_topics || 0);
    } catch (error) {
      // If either API call fails, catch the error
      setError(new Error(error.message || "Failed to generate or fetch new topics."));
    } finally {
      setFetching(false); // Stop the spinning wheel regardless of the outcome
    }
  };

  return (
    <>
      <Box
        sx={{
          boxShadow: 2,
          borderRadius: 2,
          p: 2,
          width: "100%",
          bgcolor: "#fff",
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            mb: 2, // Margin bottom for spacing below this box
          }}
        >
          {/* Central elements */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              mb: -3, // Spacing below the central elements, before the headers
            }}
          >
            <Button variant="contained" onClick={generateInsightsDummy}>
              Generate New Topic Insights
            </Button>
            <Typography variant="body1" sx={{ ml: 2, mr: 2 }}>
              {lastGeneratedTimestamp
                ? `Last generated: ${lastGeneratedTimestamp}`
                : "Not generated yet"}
            </Typography>
          </Box>

          {/* Headers on the line below */}
          <Box
            sx={{
              width: "95%", // Ensures the header takes the full width
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mt: 5, // Margin top for spacing above the headers if needed
            }}
          >
            <Typography>Topic Title</Typography>
            <Typography># of queries in topic</Typography>
          </Box>
        </Box>
        <List>
          {currentTopics.length > 0
            ? currentTopics.map((topic, index) => (
                <ListItem
                  button
                  key={index}
                  selected={selectedTopic === topic}
                  onClick={() => selectTopic(topic)}
                >
                  <ListItemText primary={topic.name} />
                  <Chip label={topic.topic_popularity} color="primary" />
                </ListItem>
              ))
            : [...Array(5)].map((_, index) => (
                <ListItem key={index} disabled>
                  <ListItemText primary="    " />
                  <Chip label="" />
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
              {selectedTopic?.examples.length > 0 ? (
                selectedTopic.examples.map((example, index) => (
                  <TableRow key={index}>
                    <TableCell sx={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                      {example.timestamp}
                    </TableCell>
                    <TableCell sx={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                      {example.userQuestion}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={2} align="center">
                    Select a topic to view example queries
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        {fetching ? (
          <CircularProgress
            size={24}
            sx={{
              position: "absolute",
              top: 8, // Adjust as necessary
              right: 8,
              zIndex: (theme) => theme.zIndex.tooltip,
            }}
          />
        ) : null}
      </Box>
      {/* Place the Dialog here. It's okay if it's rendered over the Box. */}
      <Dialog open={showPopup} onClose={() => setShowPopup(false)}>
        <DialogContent>
          <DialogContentText>
            {" "}
            <DialogContentText>
              There are currently no generated topics for this time period
            </DialogContentText>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowPopup(false)}>Close</Button>
          <Button onClick={handleGenerateNewTopics} color="primary" autoFocus>
            Generate {timePeriod} level insights
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default Insights;
