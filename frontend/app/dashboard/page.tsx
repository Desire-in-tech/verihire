import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { applications, jobs } from "@/lib/verihire-data";

export default function DashboardPage() {
  return (
    <AppShell active="/dashboard" title="Good morning, Trina." subtitle="Here’s what’s happening with your applications.">
      <div className="space-y-6">
        <div className="rounded-[28px] border border-[#204d48] bg-[#101d1d] p-6 text-[#edf3f8]">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8fe0ca]">Your privacy impact</div>
          <div className="text-3xl font-semibold tracking-[-0.05em]">0 unnecessary disclosures</div>
          <p className="mt-2 text-[#b6c4d1]">Only verified qualifications were shared with employers.</p>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["Applications", "6"],
            ["Verified", "4"],
            ["Matched jobs", "12"],
            ["Pending", "2"],
          ].map(([label, value]) => (
            <Card key={label} className="p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#9aa7b8]">{label}</div>
              <div className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-white">{value}</div>
            </Card>
          ))}
        </div>

        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold tracking-[-0.05em] text-white">Recommended for you</h2>
          <Button href="/jobs" variant="ghost">View all →</Button>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          {jobs.slice(0, 2).map((job) => (
            <Card key={job.id} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#162127] text-lg font-semibold text-[#7adcc8]">
                    {job.logo}
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">{job.role}</h3>
                    <div className="text-sm text-[#9aa7b8]">{job.company} · {job.location}</div>
                  </div>
                </div>
                <div className="text-sm font-semibold text-[#7adcc8]">{job.match}% match</div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {job.skills.map((skill) => (
                  <Badge key={skill} tone="cyan">✓ {skill}</Badge>
                ))}
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                <Badge tone="green">✓ Employer verified</Badge>
                <Badge tone="purple">◇ Privacy verification available</Badge>
              </div>

              <div className="mt-5">
                <Button href={`/verify`} variant="secondary">Check eligibility</Button>
              </div>
            </Card>
          ))}
        </div>

        <div className="rounded-2xl border border-[#1d2530] bg-[#0f1620] p-5">
          <h3 className="mb-4 text-xl font-semibold text-white">Recent application timeline</h3>
          <div className="space-y-3">
            {applications.map((app) => (
              <div key={app.id} className="flex items-center justify-between rounded-xl border border-[#1d2530] bg-[#0b1118] p-3">
                <div>
                  <div className="font-medium text-white">{app.company}</div>
                  <div className="text-sm text-[#9aa7b8]">{app.role}</div>
                </div>
                <Badge tone={app.status === "Verification" ? "cyan" : "slate"}>{app.status}</Badge>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
