import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function VerifyPage() {
  return (
    <AppShell active="/verify" title="Verification" subtitle="Prove your eligibility privately.">
      <Card className="max-w-3xl p-6">
        <h2 className="text-2xl font-semibold tracking-[-0.05em] text-white">Midnight verification follows a CV upload</h2>
        <p className="mt-3 text-[#9aa7b8]">
          Upload a PDF CV on your profile. VeriHire extracts credentials, evaluates the selected job, and asks Midnight to prove eligibility. This page does not store a verification of its own.
        </p>
        <div className="mt-6">
          <Button href="/profile">Upload a CV</Button>
        </div>
      </Card>
    </AppShell>
  );
}
