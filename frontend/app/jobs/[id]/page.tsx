import { notFound } from "next/navigation";
import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { jobs } from "@/lib/verihire-data";

export default async function JobDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const job = jobs.find((item) => item.id === id) ?? jobs[0];

  if (!job) {
    notFound();
  }

  return (
    <AppShell active="/jobs" title={job.role} subtitle={`${job.company} · ${job.location} · ${job.type}`}>
      <div className="grid gap-6 xl:grid-cols-[1.6fr_0.8fr]">
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#162127] text-xl font-semibold text-[#7adcc8]">
                {job.logo}
              </div>
              <div>
                <h2 className="text-3xl font-semibold tracking-[-0.06em] text-white">{job.role}</h2>
                <p className="text-[#9aa7b8]">{job.company} · {job.location} · {job.type}</p>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              {job.skills.map((skill) => (
                <Badge key={skill} tone="cyan">✓ {skill}</Badge>
              ))}
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="mb-3 text-xl font-semibold text-white">About the role</h3>
            <p className="text-[#9aa7b8]">{job.desc}</p>
          </Card>

          <Card className="p-6">
            <h3 className="mb-4 text-xl font-semibold text-white">Required qualifications</h3>
            <div className="space-y-3">
              {job.requirements.map((requirement, index) => (
                <div key={requirement} className="flex items-center justify-between gap-4 rounded-xl border border-[#1d2530] bg-[#0b1118] p-3">
                  <div>
                    <div className="font-medium text-[#edf3f8]">{requirement}</div>
                    <div className="text-xs uppercase tracking-[0.12em] text-[#9aa7b8]">
                      {index === 0 ? "Required" : "Relevant experience"}
                    </div>
                  </div>
                  <div className="text-[#7adcc8]">✓</div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="p-6">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl border border-[#2a3747] bg-[#121d26] text-[#7adcc8]">
              ◇
            </div>
            <h3 className="text-xl font-semibold text-white">Privacy-first application</h3>
            <p className="mt-2 text-[#9aa7b8]">Verify your eligibility without initially revealing your full CV.</p>
            <div className="mt-5">
              <Button href="/verify">Check my eligibility</Button>
            </div>
          </Card>

          <Card className="p-6">
            <Badge tone="green">✓ Employer verified</Badge>
            <p className="mt-3 text-sm text-[#9aa7b8]">Identity and company details have been independently verified.</p>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}
