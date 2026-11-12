/**
 * Lightweight stand-in for `recharts`, for use with
 *   vi.mock("recharts", () => import("<path>/rechartsMock"));
 *
 * jsdom has no layout engine, so real recharts renders no ticks or tooltips
 * and our tickFormatter/labelFormatter callbacks never run. These fakes render
 * just enough DOM to assert on what *our* code computes:
 * - XAxis renders every row's tick through `tickFormatter` (list "x-axis").
 * - YAxis exposes its `domain` prop as data-domain.
 * - Tooltip renders its `content` element twice: once active for the first
 *   data row, and once with a payload that has no row data (to exercise the
 *   "no timestamp" fallback in our label formatters).
 * - Legend renders a marker so tests can check whether it's shown.
 * - Line/Bar render a marker per series key.
 */
import React, { createContext, useContext } from "react";

type Row = Record<string, unknown>;

const DataContext = createContext<Row[]>([]);

const Chart = ({ data = [], children }: { data?: Row[]; children?: React.ReactNode }) => (
  <DataContext.Provider value={data}>
    <div data-testid="chart">{children}</div>
  </DataContext.Provider>
);

export const BarChart = Chart;
export const LineChart = Chart;

export const ResponsiveContainer = ({ children }: { children?: React.ReactNode }) => (
  <>{children}</>
);

export const CartesianGrid = () => null;

export const XAxis = ({
  dataKey,
  tickFormatter,
}: {
  dataKey: string;
  tickFormatter?: (value: unknown, index: number) => string;
}) => {
  const data = useContext(DataContext);
  return (
    <ul aria-label="x-axis">
      {data.map((row, i) => (
        <li key={i}>
          {tickFormatter ? tickFormatter(row[dataKey], i) : String(row[dataKey])}
        </li>
      ))}
    </ul>
  );
};

export const YAxis = ({ domain }: { domain?: unknown }) => (
  <div data-testid="y-axis" data-domain={JSON.stringify(domain)} />
);

export const Tooltip = ({ content }: { content?: React.ReactElement }) => {
  const data = useContext(DataContext);
  if (!content) return null;
  const item = (payload: Row) => ({ dataKey: "value", name: "value", value: 1, payload });
  return (
    <>
      {data.length > 0 && (
        <div data-testid="tooltip">
          {React.cloneElement(content as React.ReactElement<Row>, {
            active: true,
            payload: [item(data[0])],
          })}
        </div>
      )}
      <div data-testid="tooltip-empty">
        {React.cloneElement(content as React.ReactElement<Row>, {
          active: true,
          payload: [item({})],
        })}
      </div>
    </>
  );
};

export const Legend = () => <div data-testid="legend" />;

export const Line = ({ dataKey }: { dataKey: string }) => (
  <span data-testid={`line-${dataKey}`} />
);

export const Bar = ({ dataKey }: { dataKey: string }) => (
  <span data-testid={`bar-${dataKey}`} />
);
