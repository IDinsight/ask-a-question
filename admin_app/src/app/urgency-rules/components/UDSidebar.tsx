import React, { useState } from "react";

import { Close } from "@mui/icons-material";
import { Box, Fade, IconButton, Link, Modal, Typography } from "@mui/material";

import { sizes } from "@/utils";
import { apiCalls } from "@/utils/api";
import { TestSidebar } from "@/components/SidebarCommon";
import TypingAnimation from "@/components/TypingAnimation";

interface UDResults {
  is_urgent: boolean;
  matched_rules: string[];
}

interface UDResponseBoxData {
  dateTime: string;
  parsedData: UDResults | string; // string is for error messages
  rawJson: string;
}

interface UDResponseBoxProps {
  loading: boolean;
  responseBoxData: UDResponseBoxData | null;
}

const getUDResponse = (
  question: string,
  generateLLMResponse: boolean, // Unused. Has to match signature of getSearchResponse
  setLoading: React.Dispatch<React.SetStateAction<boolean>>,
  setResponse: React.Dispatch<React.SetStateAction<UDResponseBoxData | null>>,
  token: string | null,
) => {
  const processUDResponse = (response: any) => {
    const udResults: UDResults = {
      is_urgent: response.is_urgent,
      matched_rules: response.matched_rules,
    };

    setResponse({
      dateTime: new Date().toISOString(),
      parsedData: udResults,
      rawJson: response,
    });
  };

  const processErrorMessage = (error: Error) => {
    setResponse({
      dateTime: new Date().toISOString(),
      parsedData: "API call failed. See <json> for details.",
      rawJson: `{error: ${error.message}}`,
    });
  };

  if (question === "") {
    return;
  }
  setLoading(true);
  if (token) {
    apiCalls
      .getUrgencyDetection(question, token)
      .then((response) => {
        processUDResponse(response);
      })
      .catch((error: Error) => {
        processErrorMessage(error);
        console.error(error);
      })
      .finally(() => {
        setLoading(false);
      });
  }
};

const RenderUDResponse = ({ parsedData }: { parsedData: UDResults }) => {
  return (
    <Box display="flex" flexDirection="column">
      <Typography component={"span"} variant="subtitle2">
        Classification
      </Typography>
      <Typography
        component={"span"}
        variant="subtitle1"
        paddingBottom={sizes.doubleBaseGap}
      >
        {parsedData.is_urgent ? "Urgent" : "Not urgent"}
      </Typography>
      {parsedData.is_urgent && (
        <Typography component={"span"} variant="subtitle2" paddingBottom={1}>
          {parsedData.matched_rules.length === 1 ? "Matched Rule" : "Matched Rules"}
        </Typography>
      )}
      {parsedData.matched_rules.map((text: string) => (
        <Box sx={{ paddingBottom: 1 }} key={1}>
          <Typography component={"span"} variant="body2">
            {parsedData.matched_rules.length === 1 ? "" : "•"} {text}
          </Typography>
        </Box>
      ))}
    </Box>
  );
};

const UDResponseBox: React.FC<UDResponseBoxProps> = ({ loading, responseBoxData }) => {
  if (!responseBoxData) {
    return;
  }

  const [jsonModalOpen, setJsonModalOpen] = useState<boolean>(false);
  const toggleJsonModal = (): void => setJsonModalOpen(!jsonModalOpen);

  if (loading) {
    return <TypingAnimation />;
  } else {
    return (
      <>
        <Box display="flex" flexDirection="column" justifyContent="center">
          {/* if type is string, there was an error */}
          {typeof responseBoxData.parsedData === "string" ? (
            <Typography variant="body1">{responseBoxData.parsedData}</Typography>
          ) : (
            <RenderUDResponse parsedData={responseBoxData.parsedData} />
          )}
          <Box
            style={{
              marginTop: "5px",
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "center",
            }}
          >
            <Link
              onClick={toggleJsonModal}
              variant="caption"
              align="right"
              underline="hover"
              sx={{ cursor: "pointer" }}
            >
              {"<json>"}
            </Link>
          </Box>
        </Box>

        <Modal
          open={jsonModalOpen}
          onClose={toggleJsonModal}
          aria-labelledby="modal-modal-title"
          aria-describedby="modal-modal-description"
        >
          <Fade in={jsonModalOpen}>
            <Box
              sx={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                width: "80%",
                maxHeight: "80%",
                flexGrow: 1,
                p: 4,
                boxShadow: 24,
                overflow: "scroll",
                borderRadius: "10px",
                bgcolor: "background.paper",
              }}
            >
              <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                <IconButton onClick={toggleJsonModal}>
                  <Close />
                </IconButton>
              </Box>
              <Typography
                component={"span"}
                id="modal-modal-description"
                sx={{ marginTop: 2 }}
              >
                <pre
                  style={{
                    backgroundColor: "#f5f5f5",
                    border: "1px solid #ccc",
                    padding: "10px",
                    borderRadius: "10px",
                    overflowX: "auto",
                    fontFamily: "Courier, monospace",
                  }}
                >
                  {"rawJson" in responseBoxData
                    ? JSON.stringify(responseBoxData.rawJson, null, 2)
                    : "No JSON data found"}
                </pre>
              </Typography>
            </Box>
          </Fade>
        </Modal>
      </>
    );
  }
};

const UDSidebar = ({ closeSidebar }: { closeSidebar: () => void }) => {
  return (
    <TestSidebar
      title="Test Urgency Detection"
      closeSidebar={closeSidebar}
      showLLMResponseToggle={false}
      handleSendClick={getUDResponse}
      ResponseBox={UDResponseBox}
    />
  );
};

export { UDSidebar };
export type { UDResponseBoxData };
