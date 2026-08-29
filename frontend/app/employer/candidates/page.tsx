import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function EmployerCandidatesPage() {
  return (
    <AppShell mode="employer" active="/employer/candidates" title="Candidates" subtitle="Review privacy-preserving profiles.">
      <Card className="max-w-2xl p-8 text-center">
        <p className="text-lg text-[#dfeaf8]">Select verified candidates without viewing unnecessary personal data.</p>
        <div className="mt-6">
          <Button href="/employer">View dashboard</Button>
        </div>
      </Card>
    </AppShell>
  );
}
