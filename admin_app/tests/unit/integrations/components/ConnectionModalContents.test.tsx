import { render, screen } from "@testing-library/react";

import {
  GlificModalContent,
  RestApiContent,
  TurnModalContent,
  TypebotModalContent,
} from "@/components/features/integrations/components/ConnectionModalContents";

// Every external link must open in a new tab without leaking the opener.
const expectExternal = (link: HTMLElement, hrefPart: string) => {
  expect(link).toHaveAttribute("href", expect.stringContaining(hrefPart));
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
};

describe("ConnectionModalContents", () => {
  it("Typebot: links to the downloadable template and names the API_KEY field", () => {
    render(<TypebotModalContent />);
    expectExternal(
      screen.getByRole("link", { name: "AI response with feedback" }),
      "typebot_demo_flow.json",
    );
    expect(screen.getByText("API_KEY")).toBeInTheDocument();
  });

  it("Turn: links to the playbook and the docs", () => {
    render(<TurnModalContent />);
    expectExternal(
      screen.getByRole("link", { name: "Open Turn Playbook" }),
      "whatsapp.turn.io",
    );
    expectExternal(
      screen.getByRole("link", { name: "documentation" }),
      "turn.io/turn",
    );
  });

  it("Glific: links to the flow and the docs, and names the key placeholder", () => {
    render(<GlificModalContent />);
    expectExternal(
      screen.getByRole("link", { name: "Open Glific Flow" }),
      "search_flow_without_feedback.json",
    );
    expectExternal(
      screen.getByRole("link", { name: "documentation" }),
      "glific/glific",
    );
    expect(screen.getByText("INSERT_AAQ_API_KEY")).toBeInTheDocument();
  });

  it("REST API: links to the API docs", () => {
    render(<RestApiContent />);
    expectExternal(
      screen.getByRole("link", { name: "REST API documentation" }),
      "/api/docs",
    );
  });
});
