import React, { useState, useEffect } from "react";
import axios from "axios";
import styled from "styled-components";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";
import { useAuth } from "@/utils/auth";
import Pagination from "@mui/material/Pagination";

interface Topic {
  name: string;
  examples: { timestamp: string; userQuestion: string }[];
  topic_popularity: string;
}

interface TopicsResponse {
  n_topics: number;
}

const TopicsContainer = styled.div`
  background-color: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
`;

const TopicsList = styled.ul`
  list-style-type: none;
  padding: 0;
  margin: 0;
  width: 100%;
`;

const TopicItem = styled.li<{ selected: boolean }>`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
  background-color: ${({ selected }) => (selected ? "#f0f0f0" : "transparent")};
  &:last-child {
    border-bottom: none;
  }
  cursor: pointer;
`;

const TopicName = styled.span`
  font-weight: 500;
`;

const TopicPopularity = styled.span<{ color: string }>`
  background-color: ${({ color }) => color};
  color: white;
  border-radius: 4px;
  padding: 4px;
`;

const ExampleSentencesContainer = styled.div`
  flex-grow: 1;
  margin-left: 16px;
`;

const ExampleTable = styled.table`
  width: 100%;
  border-collapse: collapse;
`;

const ExampleTableRow = styled.tr`
  &:nth-child(even) {
    background-color: #f9f9f9;
  }
`;

const ExampleTableCell = styled.td<{ istimestamp: boolean }>`
  padding: 8px;
  border: 1px solid #ddd;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: ${({ istimestamp }) => (istimestamp ? "150px" : "350px")};
`;

const ExampleTableHeader = styled.th`
  padding: 8px;
  border: 1px solid #ddd;
  text-align: left;
  background-color: #f2f2f2;
`;

const LoadingOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
`;

const PaginationContainer = styled.div`
  margin-top: 16px;
  display: flex;
  justify-content: center;
`;

const TopicsSection: React.FC = () => {
  const { token } = useAuth();
  const [topics, setTopics] = useState<Topic[]>([]);
  const [n_topics, setNTopics] = useState<number>(0);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const topicsPerPage = 5;

  const getTopicColor = (popularity: string) => {
    switch (popularity) {
      case "High":
        return "red";
      case "Medium":
        return "orange"; // Changed from yellow for better visibility
      case "Low":
        return "green";
      default:
        return "gray"; // Fallback for unknown popularity levels
    }
  };

  useEffect(() => {
    const fetchTopics = async () => {
      try {
        const response = await axios.get(
          "http://localhost:8000/dashboard/insights/topics",
          {
            headers: { Authorization: `Bearer ${token}` },
          },
        );

        const fetchedTopics = response.data.topics.map((topic: any) => ({
          name: topic.topic_name,
          topic_popularity: topic.topic_popularity,
          examples: topic.topic_samples.map((sample: string) => ({
            timestamp: "2024-07-23 06:01PM", // Placeholder timestamp
            userQuestion: sample,
          })),
        }));
        const nTopics = response.data.n_topics;
        setTopics(fetchedTopics);
        setNTopics(nTopics);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching topics:", err);
        setError("Failed to load topics");
        setLoading(false);
      }
    };

    fetchTopics();
  }, []);

  // Calculate total pages based on the number of topics
  const totalPages = Math.ceil(n_topics / topicsPerPage);
  // Get topics for the current page
  const currentTopics = topics.slice(
    (currentPage - 1) * topicsPerPage,
    currentPage * topicsPerPage,
  );

  const handlePageChange = (
    _event: React.ChangeEvent<unknown>,
    value: number,
  ) => {
    setCurrentPage(value);
  };

  if (loading)
    return (
      <LoadingOverlay>
        <Box display="flex" flexDirection="column" alignItems="center">
          <CircularProgress size={60} />
          <p>Generating insights...</p>
        </Box>
      </LoadingOverlay>
    );

  if (error) return <p>{error}</p>;

  return (
    <TopicsContainer>
      <TopicsList>
        {currentTopics.map((topic, index) => (
          <TopicItem
            key={index}
            onClick={() => setSelectedTopic(topic)}
            selected={selectedTopic?.name === topic.name}
          >
            <TopicName>{topic.name}</TopicName>
            <TopicPopularity color={getTopicColor(topic.topic_popularity)}>
              {topic.topic_popularity}
            </TopicPopularity>
          </TopicItem>
        ))}
      </TopicsList>
      <PaginationContainer>
        <Pagination
          count={totalPages}
          page={currentPage}
          onChange={handlePageChange}
          color="primary"
        />
      </PaginationContainer>
      <ExampleSentencesContainer>
        <ExampleTable>
          <thead>
            <tr>
              <ExampleTableHeader>Timestamp</ExampleTableHeader>
              <ExampleTableHeader>User Question</ExampleTableHeader>
            </tr>
          </thead>
          <tbody>
            {selectedTopic ? (
              selectedTopic.examples.map((example, index) => (
                <ExampleTableRow key={index}>
                  <ExampleTableCell istimestamp={true}>
                    {example.timestamp}
                  </ExampleTableCell>
                  <ExampleTableCell>{example.userQuestion}</ExampleTableCell>
                </ExampleTableRow>
              ))
            ) : (
              <tr>
                <td colSpan={2}>Select a topic to see examples.</td>
              </tr>
            )}
          </tbody>
        </ExampleTable>
      </ExampleSentencesContainer>
    </TopicsContainer>
  );
};

export default TopicsSection;
