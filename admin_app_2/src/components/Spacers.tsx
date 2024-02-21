import { css } from "@emotion/react";
import styled from "@emotion/styled";
import { sizes } from "../utils";
interface SpacerProps {
  width?: string;
  height?: string;
}

const Spacer = styled.div<SpacerProps>`
  ${(props) => css`
    width: ${props.width};
    height: ${props.height};
  `}
`;

interface BaseProps {
  horizontal?: boolean;
}

const Base = ({ horizontal }: BaseProps) => {
  return (
    <Spacer
      height={!horizontal ? sizes.baseGap : "0"}
      width={horizontal ? sizes.baseGap : "0"}
    />
  );
};

interface SpacerProps {
  width?: string;
  height?: string;
}

const Tiny = ({ horizontal }: BaseProps) => {
  return (
    <Spacer
      height={!horizontal ? sizes.tinyGap : "0"}
      width={horizontal ? sizes.tinyGap : "0"}
    />
  );
};

const Small = ({ horizontal }: BaseProps) => {
  return (
    <Spacer
      height={!horizontal ? sizes.smallGap : "0"}
      width={horizontal ? sizes.smallGap : "0"}
    />
  );
};

const DoubleBase = ({ horizontal }: BaseProps) => {
  return (
    <Spacer
      height={!horizontal ? sizes.doubleBaseGap : "0"}
      width={horizontal ? sizes.doubleBaseGap : "0"}
    />
  );
};

export const Spacers = {
  Spacer,
  Base,
  Tiny,
  Small,
  DoubleBase,
};
