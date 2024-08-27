import { keyframes } from "@emotion/react";
import styled from "@emotion/styled";

import { Box } from "@mui/material";

// For 3-dot typing animation
const typing = keyframes`
  from { opacity: 0 }
  to { opacity: 1 }
`;
const Fader = styled("div")`
  animation: ${typing} 1s infinite;
  &:nth-of-type(2) {
    animation-delay: 0.2s;
  }
  &:nth-of-type(3) {
    animation-delay: 0.4s;
  }
`;
const TypingAnimation = () => {
  return (
    <Box sx={{ display: "flex", fontSize: "1.3rem" }}>
      <Fader>.</Fader>
      <Fader>.</Fader>
      <Fader>.</Fader>
    </Box>
  );
};

export default TypingAnimation;
