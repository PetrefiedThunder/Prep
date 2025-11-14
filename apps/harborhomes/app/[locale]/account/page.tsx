import { Card, CardContent, CardHeader, CardTitle, Input, Label, Button } from '@/components/ui';

export default function AccountPage() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="name">Name</Label>
            <Input id="name" defaultValue="Jordan Guest" />
          </div>
          <div>
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" defaultValue="+1 555-000-0000" />
          </div>
          <Button>Save changes</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-ink">
          <label className="flex items-center gap-2">
            <input type="checkbox" defaultChecked /> Email updates
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" /> SMS reminders
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" defaultChecked /> Promotions
          </label>
        </CardContent>
      </Card>
    </div>
  );
}
