import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { verifications } from "@/lib/verihire-data";

export default function VerifyPage() {
  return (
    <AppShell active="/verify" title="Verification" subtitle="Prove your eligibility privately.">
      <div className="space-y-6">
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#182230] text-2xl text-[#7adcc8]">✦</div>
            <div>
              <h2 className="text-2xl font-semibold tracking-[-0.05em] text-white">Verify your eligibility</h2>
              <p className="text-[#9aa7b8]">We compare relevant qualifications with job requirements and keep your source information private.</p>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-[#1d2530] bg-[#0b1118] p-5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="purple">AI Analysis</Badge>
              <Badge tone="cyan">◇ Powered by Midnight</Badge>
            </div>
            <h3 className="mt-4 text-2xl font-semibold text-white">Ready to create a private proof?</h3>
            <p className="mt-2 text-[#9aa7b8]">This verifies Python, PostgreSQL, and AWS qualifications for Acme Technologies.</p>
            <div className="mt-5">
              <Button>Generate private verification</Button>
            </div>
          </div>
        </Card>

        <div className="grid gap-5 lg:grid-cols-3">
          {verifications.map((item) => (
            <Card key={item.id} className="p-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="text-lg font-semibold text-white">{item.title}</h3>
                <Badge tone={item.status === "Verified" ? "green" : item.status === "Pending" ? "cyan" : "amber"}>{item.status}</Badge>
              </div>
              <p className="text-sm text-[#9aa7b8]">{item.summary}</p>
              <div className="mt-4 space-y-2">
                {item.facts.map((fact) => (
                  <div key={fact} className="rounded-lg border border-[#1d2530] bg-[#0b1118] px-3 py-2 text-sm text-[#dfeaf8]">{fact}</div>
                ))}
              </div>
              <div className="mt-4 text-xs uppercase tracking-[0.18em] text-[#85d8cc]">Proof ID {item.proofId}</div>
            </Card>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
