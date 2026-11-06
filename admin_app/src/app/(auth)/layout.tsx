import Image from "next/image";
import { IconFilePlus, IconMessageCircle, IconPlug } from "@tabler/icons-react";

// The three onboarding steps shown on the navy marketing panel.
const STEPS = [
  {
    title: "Create",
    description: "Add your FAQs as easy-to-manage cards",
    Icon: IconFilePlus,
  },
  {
    title: "Test",
    description: "Check if the responses sound right",
    Icon: IconMessageCircle,
  },
  {
    title: "Integrate",
    description: "Connect to your chatbot using our APIs. You are all set",
    Icon: IconPlug,
  },
];

/**
 * Shared shell for the signed-out screens (sign in, reset password).
 * Left: navy marketing panel. Right: the page's form, centred.
 * On narrow screens the panel wraps above the form.
 */
export default function AuthLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex min-h-screen flex-wrap bg-background text-sm text-foreground">
      <section className="flex flex-[1_1_560px] flex-col justify-between gap-12 bg-sidebar p-8 text-sidebar-foreground md:p-14">
        <Image
          src="/logo-light.png"
          alt="Ask A Question by IDinsight"
          width={1200}
          height={214}
          priority
          className="h-auto w-60"
        />

        <div className="flex max-w-130 flex-col gap-8">
          <h2 className="text-3xl leading-tight font-semibold tracking-tight md:text-4xl">
            Integrate automated question answering into your chatbot in 3 simple steps
          </h2>

          <ol className="flex flex-col gap-5">
            {STEPS.map(({ title, description, Icon }) => (
              <li key={title} className="flex items-start gap-3.5">
                <span className="flex size-10 flex-none items-center justify-center border border-sidebar-primary/50 text-sidebar-primary">
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <div>
                  <h3 className="text-base font-semibold">{title}</h3>
                  <p className="text-sidebar-foreground/80">{description}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        {/* Empty spacer so justify-between keeps the copy vertically centred. */}
        <div aria-hidden="true" className="hidden md:block" />
      </section>

      <main className="flex flex-[1_1_480px] items-center justify-center px-6 py-12">
        {children}
      </main>
    </div>
  );
}
