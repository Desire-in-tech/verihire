import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { jobs } from "@/lib/verihire-data";

export default function JobsPage() {
  return (
    <AppShell active="/jobs" title="Find opportunities without oversharing." subtitle="Discover roles matched to your verified skills.">
      <div className="space-y-6">
        <div className="grid gap-3 rounded-2xl border border-[#1d2530] bg-[#0f1620] p-4 md:grid-cols-5">
          <input
            className="rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-sm text-[#edf3f8] placeholder:text-[#77869c] outline-none focus:border-[#31d4c7]"
            placeholder="Search jobs..."
          />
          <select className="rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-sm text-[#edf3f8] outline-none focus:border-[#31d4c7]">
            <option>All roles</option>
            <option>Engineering</option>
            <option>AI & Data</option>
          </select>
          <select className="rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-sm text-[#edf3f8] outline-none focus:border-[#31d4c7]">
            <option>Any location</option>
            <option>Remote</option>
            <option>Tokyo</option>
          </select>
          <select className="rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-sm text-[#edf3f8] outline-none focus:border-[#31d4c7]">
            <option>Experience</option>
            <option>Mid-level</option>
            <option>Senior</option>
          </select>
          <Button variant="secondary">Apply filters</Button>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          {jobs.map((job) => (
            <Card key={job.id} className="p-5">
              <div className="flex items-start justify-between gap-3">
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

              <p className="mt-4 text-[#b0bdca]">{job.desc}</p>

              <div className="mt-5 flex items-center justify-between">
                <div className="flex flex-wrap gap-2">
                  <Badge tone="green">✓ Employer verified</Badge>
                  <Badge tone="purple">◇ Privacy verification</Badge>
                </div>
                <Button href={`/jobs/${job.id}`} variant="secondary">View job</Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
