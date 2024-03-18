import { css } from "@emotion/react";
import styled from "@emotion/styled";
import { Box, BoxProps } from "@mui/material";
import { sizes } from "../utils";

interface SpacerProps {
  width?: string;
  height?: string;
}

const BlankDiv = styled.div<SpacerProps>`
  ${(props) => css`
    width: ${props.width};
    height: ${props.height};
  `}
`;

interface BaseProps {
  horizontal?: boolean;
  multiplier?: number;
}

const Spacer = ({ horizontal, multiplier = 1 }: BaseProps) => {
  return (
    <BlankDiv
      height={
        !horizontal
          ? `${parseFloat(sizes.baseGap) * Number(multiplier)}px`
          : "0"
      }
      width={
        horizontal ? `${parseFloat(sizes.baseGap) * Number(multiplier)}px` : "0"
      }
    />
  );
};

const FlexBox: React.FC<BoxProps> = ({ children, ...props }) => {
  return (
    <Box display="flex" flexDirection="column" {...props}>
      {children}
    </Box>
  );
};

export const Layout = {
  Spacer,
  FlexBox,
};
