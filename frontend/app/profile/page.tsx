import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { candidateProfile } from "@/lib/verihire-data";

export default function ProfilePage() {
  return (
    <AppShell active="/profile" title="Your profile" subtitle="Your source information is encrypted and stays private.">
      <Card className="max-w-3xl p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#26313a] text-xl font-semibold text-[#edf3f8]">TR</div>
          <div>
            <h2 className="text-2xl font-semibold tracking-[-0.05em] text-white">{candidateProfile.name}</h2>
            <Badge tone="green">✓ Identity verified</Badge>
          </div>
        </div>

        <div className="mt-6 space-y-5">
          <div>
            <label className="mb-2 block text-sm text-[#dfeaf8]">Professional headline</label>
            <input
              defaultValue={candidateProfile.headline}
              className="w-full rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-[#edf3f8] outline-none focus:border-[#31d4c7]"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm text-[#dfeaf8]">Core skills</label>
            <input
              defaultValue={candidateProfile.skills.join(", ")}
              className="w-full rounded-xl border border-[#2a3440] bg-[#0b1118] px-4 py-3 text-[#edf3f8] outline-none focus:border-[#31d4c7]"
            />
          </div>

          <Button>Update profile</Button>
        </div>
      </Card>
    </AppShell>
  );
}
