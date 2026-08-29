import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <AppShell active="/settings" title="Settings" subtitle="Manage your account and privacy preferences.">
      <div className="max-w-3xl space-y-5">
        <div className="flex gap-3 rounded-2xl border border-[#1d2530] bg-[#0f1620] p-2 text-sm">
          <div className="rounded-xl px-4 py-2 text-[#9aa7b8]">Profile</div>
          <div className="rounded-xl bg-[#101821] px-4 py-2 text-[#edf3f8]">Privacy</div>
          <div className="rounded-xl px-4 py-2 text-[#9aa7b8]">Notifications</div>
        </div>

        <Card className="p-6">
          <h3 className="mb-2 text-2xl font-semibold tracking-[-0.05em] text-white">Privacy preferences</h3>
          <p className="mb-6 text-[#9aa7b8]">Choose how and when information is shared with employers.</p>

          {[
            ["Require verification first", "Verify eligibility before sharing application data."],
            ["Information request notifications", "Notify me when an employer requests more information."],
            ["Anonymous matching", "Allow matching based only on verified qualifications."],
          ].map(([title, description]) => (
            <div key={title} className="mb-5 flex items-center justify-between gap-4 rounded-xl border border-[#1d2530] bg-[#0b1118] p-4">
              <div>
                <div className="font-medium text-[#edf3f8]">{title}</div>
                <div className="text-sm text-[#9aa7b8]">{description}</div>
              </div>
              <div className="h-6 w-11 rounded-full bg-[#1b2d31] p-1">
                <div className="h-4 w-4 rounded-full bg-[#31d4c7]" />
              </div>
            </div>
          ))}

          <Button>Save changes</Button>
        </Card>
      </div>
    </AppShell>
  );
}
