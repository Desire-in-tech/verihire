import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function EmployerJobsPage() {
  return (
    <AppShell mode="employer" active="/employer/jobs" title="Job listings" subtitle="Manage your open roles.">
      <Card className="max-w-2xl p-8 text-center">
        <p className="text-lg text-[#dfeaf8]">Your active job listings appear here.</p>
        <div className="mt-6">
          <Button href="/employer">View candidates</Button>
        </div>
      </Card>
    </AppShell>
  );
}
