import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { applications } from "@/lib/verihire-data";

export default function ApplicationsPage() {
  return (
    <AppShell active="/applications" title="Your applications" subtitle="Track each application without losing control of your data.">
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          {[
            ["Total", "6"],
            ["Verified", "4"],
            ["In review", "1"],
            ["Interviews", "1"],
          ].map(([label, value]) => (
            <Card key={label} className="p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#9aa7b8]">{label}</div>
              <div className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-white">{value}</div>
            </Card>
          ))}
        </div>

        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-[#101821] text-[#9aa7b8]">
                <tr>
                  <th className="px-5 py-4 font-medium">Company</th>
                  <th className="px-5 py-4 font-medium">Role</th>
                  <th className="px-5 py-4 font-medium">Applied</th>
                  <th className="px-5 py-4 font-medium">Status</th>
                  <th className="px-5 py-4 font-medium"> </th>
                </tr>
              </thead>
              <tbody>
                {applications.map((app) => (
                  <tr key={app.id} className="border-t border-[#1c2430]">
                    <td className="px-5 py-4 text-[#edf3f8]">{app.company}</td>
                    <td className="px-5 py-4 font-medium text-[#edf3f8]">{app.role}</td>
                    <td className="px-5 py-4 text-[#9aa7b8]">{app.date}</td>
                    <td className="px-5 py-4">
                      <Badge tone={app.status === "Verification" ? "cyan" : app.status === "Interview" ? "purple" : "slate"}>{app.status}</Badge>
                    </td>
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
