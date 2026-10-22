import { AppShell } from "@/components/layout/app-shell";
import { EmployerResults } from "@/components/employer-results";

export default function EmployerCandidatesPage() {
  return (
    <AppShell mode="employer" active="/employer/candidates" title="Candidates" subtitle="Stored Midnight verification claims.">
      <EmployerResults />
    </AppShell>
  );
}
