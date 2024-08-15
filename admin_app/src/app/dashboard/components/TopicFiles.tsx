import React, { useState } from "react";
import styled from "styled-components";

interface Topic {
  name: string;
  count: number;
  examples: { timestamp: string; userQuestion: string }[];
}

interface TopicsSectionProps {
  topics: Topic[];
}

const TopicsContainer = styled.div`
  background-color: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
`;

const TopicsList = styled.ul`
  list-style-type: none;
  padding: 0;
  margin: 0;
  width: 25%;
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

const TopicCount = styled.span`
  background-color: ${({ color }) => color || "#f0f0f0"};
  color: #fff;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 0.9em;
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

const ExampleTableCell = styled.td<ExampleTableCellProps>`
  padding: 8px;
  border: 1px solid #ddd;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: ${({ isTimestamp }) => (isTimestamp ? "150px" : "350px")};
`;

const ExampleTableHeader = styled.th`
  padding: 8px;
  border: 1px solid #ddd;
  text-align: left;
  background-color: #f2f2f2;
`;

const TopicsSection: React.FC<TopicsSectionProps> = ({ topics }) => {
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);

  const getTopicColor = (index: number) => {
    const colors = ["#FFA500", "#4B0082", "#228B22"];
    return colors[index % colors.length];
  };

  return (
    <TopicsContainer>
      <TopicsList>
        {topics.map((topic, index) => (
          <TopicItem
            key={index}
            onClick={() => setSelectedTopic(topic)}
            selected={selectedTopic?.name === topic.name}
          >
            <TopicName>{topic.name}</TopicName>
            <TopicCount color={getTopicColor(index)}>{topic.count}</TopicCount>
          </TopicItem>
        ))}
      </TopicsList>
      <ExampleSentencesContainer>
        <h2>Escalated Queries</h2>
        {selectedTopic ? (
          <ExampleTable>
            <thead>
              <tr>
                <ExampleTableHeader>Timestamp</ExampleTableHeader>
                <ExampleTableHeader>User Question</ExampleTableHeader>
              </tr>
            </thead>
            <tbody>
              {selectedTopic.examples.map((example, index) => (
                <ExampleTableRow key={index}>
                  <ExampleTableCell isTimestamp={true}>
                    {example.timestamp}
                  </ExampleTableCell>
                  <ExampleTableCell>{example.userQuestion}</ExampleTableCell>
                </ExampleTableRow>
              ))}
            </tbody>
          </ExampleTable>
        ) : (
          <p>Select a topic to see examples.</p>
        )}
      </ExampleSentencesContainer>
    </TopicsContainer>
  );
};

export default TopicsSection;
