import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmployerResults } from "@/components/employer-results";

export default function EmployerDashboardPage() {
  return (
    <AppShell mode="employer" active="/employer" title="Good morning." subtitle="Midnight verification results from stored CV uploads.">
      <div className="space-y-6">
        <div className="flex items-center justify-end">
          <Button href="/employer/jobs" variant="secondary">+ Post a job</Button>
        </div>
        <EmployerResults />
      </div>
    </AppShell>
  );
}
