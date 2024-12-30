import React, { useState } from "react";

import { Close, Send } from "@mui/icons-material";
import {
  Box,
  Checkbox,
  CircularProgress,
  FormControlLabel,
  IconButton,
  Paper,
  Typography,
  TextField,
} from "@mui/material";

import { useAuth } from "@/utils/auth";
import { appColors } from "@/utils";

const TestSidebar = ({
  title,
  closeSidebar,
  showLLMResponseToggle,
  handleSendClick,
  ResponseBox,
}: {
  title: string;
  closeSidebar: () => void;
  showLLMResponseToggle: boolean;
  handleSendClick: (
    question: string,
    generateLLMResponse: boolean,
    setLoading: React.Dispatch<React.SetStateAction<boolean>>,
    setResponse: React.Dispatch<any>,
    token: string | null,
  ) => void;
  ResponseBox: React.FC<any>;
}) => {
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState("");
  const [generateLLMResponse, setGenerateLLMResponse] = useState(false);
  const [response, setResponse] = useState<any>(null); // could be SearchResponseBoxData or UDResponseBoxData
  const { token } = useAuth();

  const handleQuestionChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    setQuestion(event.target.value);
  };

  const toggleGenerateLLMResponse = () => {
    setGenerateLLMResponse((prev) => !prev);
  };

  return (
    <Paper
      elevation={2}
      sx={{
        padding: 3,
        paddingTop: 4,
        height: "100%",
      }}
    >
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        marginBottom={4}
      >
        <Typography variant="h6">{title}</Typography>
        <IconButton onClick={closeSidebar}>
          <Close />
        </IconButton>
      </Box>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          padding: 2,
          border: 1,
          borderRadius: 1,
          borderColor: "grey.400",
        }}
      >
        <TextField
          variant="standard"
          placeholder="Ask a question..."
          fullWidth
          value={question}
          onChange={handleQuestionChange}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              handleSendClick(
                question,
                generateLLMResponse,
                setLoading,
                setResponse,
                token,
              );
            }
          }}
          InputProps={{ disableUnderline: true }}
        />
        <Box
          display="flex"
          flexDirection="row"
          justifyContent={showLLMResponseToggle ? "space-between" : "flex-end"}
          paddingTop={2}
        >
          {showLLMResponseToggle && (
            <FormControlLabel
              control={
                <Checkbox
                  checked={generateLLMResponse}
                  onChange={toggleGenerateLLMResponse}
                  sx={{
                    color: "#5480D1",
                    "&.Mui-checked": { color: "#5480D1" },
                  }}
                />
              }
              label="Also generate AI response"
            />
          )}
          <IconButton
            onClick={() =>
              handleSendClick(
                question,
                generateLLMResponse,
                setLoading,
                setResponse,
                token,
              )
            }
            sx={{ color: generateLLMResponse ? "#5480D1" : appColors.primary }}
            disabled={loading || question == "" ? true : false}
          >
            {loading ? <CircularProgress size={24} /> : <Send />}
          </IconButton>
        </Box>
      </Box>
      <Box
        sx={{
          marginTop: 4,
          marginBottom: 4,
          padding: 4,
          overflowY: "scroll",
          border: 1,
          borderRadius: 1,
          borderColor: "grey.400",
          flexGrow: 1,
          height: "65vh",
        }}
      >
        {ResponseBox && (
          <ResponseBox loading={loading} responseBoxData={response} token={token} />
        )}
      </Box>
    </Paper>
  );
};

export { TestSidebar };
