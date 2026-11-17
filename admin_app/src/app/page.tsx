import { redirect } from "next/navigation";

/**
 * "/" has no page of its own: send people to the content page. A server
 * redirect avoids rendering an empty page first. Signed-out users are then
 * sent on to /login by the (protected) layout.
 */
export default function Home() {
  redirect("/content");
}
