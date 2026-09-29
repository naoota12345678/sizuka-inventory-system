import { redirect } from "next/navigation";
import { boardAllowed } from "@/lib/auth";
import Board from "@/components/Board";

export const dynamic = "force-dynamic";

export default async function Page() {
  if (!(await boardAllowed())) redirect("/login");
  return <Board />;
}
