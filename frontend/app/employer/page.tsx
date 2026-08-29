import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { employerCandidates } from "@/lib/verihire-data";

export default function EmployerDashboardPage() {
  return (
    <AppShell mode="employer" active="/employer" title="Good morning." subtitle="Manage hiring with better signals and less unnecessary data.">
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["Active jobs", "4"],
            ["Candidates", "82"],
            ["Verified candidates", "37"],
            ["Pending reviews", "14"],
          ].map(([label, value]) => (
            <Card key={label} className="p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#9aa7b8]">{label}</div>
              <div className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-white">{value}</div>
            </Card>
          ))}
        </div>

        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold tracking-[-0.05em] text-white">Candidate verifications</h2>
          <Button href="/employer/jobs" variant="secondary">+ Post a job</Button>
        </div>

        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-[#101821] text-[#9aa7b8]">
                <tr>
                  <th className="px-5 py-4 font-medium">Candidate</th>
                  <th className="px-5 py-4 font-medium">Role</th>
                  <th className="px-5 py-4 font-medium">Match</th>
                  <th className="px-5 py-4 font-medium">Verification</th>
                  <th className="px-5 py-4 font-medium"> </th>
                </tr>
              </thead>
              <tbody>
                {employerCandidates.map((candidate) => (
                  <tr key={candidate.id} className="border-t border-[#1c2430]">
                    <td className="px-5 py-4 font-medium text-[#edf3f8]">Candidate {candidate.id.toUpperCase()}</td>
                    <td className="px-5 py-4 text-[#edf3f8]">{candidate.role}</td>
                    <td className="px-5 py-4 text-[#7adcc8]">{candidate.match}%</td>
                    <td className="px-5 py-4"><Badge tone={candidate.status === "Verified" ? "green" : "amber"}>{candidate.status}</Badge></td>
                    <td className="px-5 py-4 text-[#7adcc8]">→</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
