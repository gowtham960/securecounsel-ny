"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type DemoUser = {
  user_email: string;
  display_name: string;
  role: string;
  allowed_matter_ids: string[];
};

type Matter = {
  matter_id: string;
  matter_name: string;
  client_name: string;
  matter_type: string;
  status: string;
  description: string;
  primary_document: string;
  created_by?: string;
  created_at?: string;
};

type MatterAssignment = {
  assignment_id: string;
  user_email: string;
  matter_id: string;
  assigned_role: string;
  assigned_by: string;
  assigned_at: string;
};

const DEMO_USERS: DemoUser[] = [
  {
    user_email: "attorney@demo-law.com",
    display_name: "Ava Johnson",
    role: "Attorney",
    allowed_matter_ids: ["matter_acme_smith", "matter_omega_contract"],
  },
  {
    user_email: "paralegal@demo-law.com",
    display_name: "Ben Carter",
    role: "Paralegal",
    allowed_matter_ids: ["matter_acme_smith"],
  },
  {
    user_email: "admin@demo-law.com",
    display_name: "Maria Lopez",
    role: "Firm Admin",
    allowed_matter_ids: ["*"],
  },
];

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5 shadow-xl">
      <h2 className="mb-4 text-lg font-semibold text-white">{title}</h2>
      {children}
    </section>
  );
}

function Pill({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | null | undefined;
}) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/70 px-3 py-2">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold text-slate-100">
        {value === null || value === undefined ? "N/A" : String(value)}
      </p>
    </div>
  );
}

export default function AdminPage() {
  const [selectedUserEmail, setSelectedUserEmail] =
    useState("admin@demo-law.com");
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [matters, setMatters] = useState<Matter[]>([]);
  const [assignments, setAssignments] = useState<MatterAssignment[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [newMatter, setNewMatter] = useState({
    matter_name: "",
    client_name: "",
    matter_type: "",
    status: "Active",
    description: "",
    primary_document: "",
  });

  const [newAssignment, setNewAssignment] = useState({
    user_email: "attorney@demo-law.com",
    matter_id: "",
    assigned_role: "Attorney",
  });

  const selectedUser = useMemo(() => {
    return (
      DEMO_USERS.find((user) => user.user_email === selectedUserEmail) ??
      DEMO_USERS[2]
    );
  }, [selectedUserEmail]);

  async function adminFetch(path: string, options: RequestInit = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "x-demo-user": selectedUserEmail,
        ...(options.headers || {}),
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || `Request failed. Status ${response.status}`
      );
    }

    return data;
  }

  async function loadAdminData() {
    setIsLoading(true);
    setError(null);
    setMessage("");

    try {
      const [usersData, mattersData, assignmentsData] = await Promise.all([
        adminFetch("/admin/users"),
        adminFetch("/admin/matters"),
        adminFetch("/admin/matter-assignments"),
      ]);

      const loadedMatters = mattersData.items || [];

      setUsers(usersData.items || []);
      setMatters(loadedMatters);
      setAssignments(assignmentsData.items || []);

      if (loadedMatters.length > 0 && !newAssignment.matter_id) {
        setNewAssignment((current) => ({
          ...current,
          matter_id: loadedMatters[0].matter_id,
        }));
      }
    } catch (err) {
      setUsers([]);
      setMatters([]);
      setAssignments([]);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load admin console data."
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function createMatter() {
    setError(null);
    setMessage("");

    try {
      const createdMatter = await adminFetch("/admin/matters", {
        method: "POST",
        body: JSON.stringify(newMatter),
      });

      setMessage(`Created matter: ${createdMatter.matter_name}`);
      setNewMatter({
        matter_name: "",
        client_name: "",
        matter_type: "",
        status: "Active",
        description: "",
        primary_document: "",
      });
      await loadAdminData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create matter.");
    }
  }

  async function assignMatter() {
    setError(null);
    setMessage("");

    try {
      const assignment = await adminFetch("/admin/matter-assignments", {
        method: "POST",
        body: JSON.stringify(newAssignment),
      });

      setMessage(
        `Assigned ${assignment.matter_id} to ${assignment.user_email} as ${assignment.assigned_role}.`
      );
      await loadAdminData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign matter.");
    }
  }

  useEffect(() => {
    void loadAdminData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedUserEmail]);

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6 shadow-2xl">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-400">
            SecureCounsel NY
          </p>
          <h1 className="mt-3 text-3xl font-bold text-white md:text-5xl">
            Admin Console
          </h1>
          <p className="mt-4 max-w-3xl text-slate-300">
            Create matters, view users, and assign matters to attorneys or
            paralegals. Backend routes enforce Firm Admin access and persist
            matters and assignments in Supabase.
          </p>

          <div className="mt-5 flex flex-wrap gap-3">
            <a
              href="/"
              className="rounded-2xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:border-cyan-400 hover:text-cyan-300"
            >
              Back to Workspace
            </a>
          </div>
        </header>

        <Section title="Admin Login Test">
          <div className="grid gap-4 md:grid-cols-3">
            {DEMO_USERS.map((user) => {
              const isSelected = user.user_email === selectedUserEmail;

              return (
                <button
                  key={user.user_email}
                  onClick={() => setSelectedUserEmail(user.user_email)}
                  className={`rounded-2xl border p-4 text-left transition ${
                    isSelected
                      ? "border-cyan-400 bg-cyan-950/40"
                      : "border-slate-800 bg-slate-900 hover:border-slate-600"
                  }`}
                >
                  <p className="text-lg font-semibold text-white">
                    {user.display_name}
                  </p>
                  <p className="mt-1 text-sm text-cyan-300">{user.role}</p>
                  <p className="mt-3 text-xs text-slate-400">
                    {user.user_email}
                  </p>
                </button>
              );
            })}
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <Pill label="Current User" value={selectedUser.display_name} />
            <Pill label="Role" value={selectedUser.role} />
            <Pill
              label="Header"
              value={`x-demo-user: ${selectedUser.user_email}`}
            />
          </div>

          {selectedUser.role !== "Firm Admin" && (
            <div className="mt-5 rounded-2xl border border-amber-800 bg-amber-950/40 p-4 text-amber-200">
              This user is not a Firm Admin. Admin API calls should return 403.
            </div>
          )}
        </Section>

        {error && (
          <div className="mt-6 rounded-2xl border border-red-800 bg-red-950/40 p-4 text-red-200">
            {error}
          </div>
        )}

        {message && (
          <div className="mt-6 rounded-2xl border border-emerald-800 bg-emerald-950/40 p-4 text-emerald-200">
            {message}
          </div>
        )}

        <div className="mt-6 grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
          <div className="space-y-6">
            <Section title="Create Matter">
              <div className="space-y-3">
                <input
                  value={newMatter.matter_name}
                  onChange={(event) =>
                    setNewMatter((current) => ({
                      ...current,
                      matter_name: event.target.value,
                    }))
                  }
                  placeholder="Matter name"
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                />

                <input
                  value={newMatter.client_name}
                  onChange={(event) =>
                    setNewMatter((current) => ({
                      ...current,
                      client_name: event.target.value,
                    }))
                  }
                  placeholder="Client name"
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                />

                <input
                  value={newMatter.matter_type}
                  onChange={(event) =>
                    setNewMatter((current) => ({
                      ...current,
                      matter_type: event.target.value,
                    }))
                  }
                  placeholder="Matter type"
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                />

                <select
                  value={newMatter.status}
                  onChange={(event) =>
                    setNewMatter((current) => ({
                      ...current,
                      status: event.target.value,
                    }))
                  }
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                >
                  <option value="Active">Active</option>
                  <option value="Restricted">Restricted</option>
                  <option value="Closed">Closed</option>
                </select>

                <input
                  value={newMatter.primary_document}
                  onChange={(event) =>
                    setNewMatter((current) => ({
                      ...current,
                      primary_document: event.target.value,
                    }))
                  }
                  placeholder="Primary document"
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                />

                <textarea
                  value={newMatter.description}
                  onChange={(event) =>
                    setNewMatter((current) => ({
                      ...current,
                      description: event.target.value,
                    }))
                  }
                  placeholder="Description"
                  className="min-h-28 w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                />

                <button
                  type="button"
                  onClick={() => void createMatter()}
                  disabled={isLoading}
                  className="w-full rounded-2xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Create Matter
                </button>
              </div>
            </Section>

            <Section title="Assign Matter">
              <div className="space-y-3">
                <select
                  value={newAssignment.user_email}
                  onChange={(event) =>
                    setNewAssignment((current) => ({
                      ...current,
                      user_email: event.target.value,
                    }))
                  }
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                >
                  {users
                    .filter((user) => user.role !== "Firm Admin")
                    .map((user) => (
                      <option key={user.user_email} value={user.user_email}>
                        {user.display_name} — {user.role}
                      </option>
                    ))}
                </select>

                <select
                  value={newAssignment.matter_id}
                  onChange={(event) =>
                    setNewAssignment((current) => ({
                      ...current,
                      matter_id: event.target.value,
                    }))
                  }
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                >
                  {matters.map((matter) => (
                    <option key={matter.matter_id} value={matter.matter_id}>
                      {matter.matter_name}
                    </option>
                  ))}
                </select>

                <select
                  value={newAssignment.assigned_role}
                  onChange={(event) =>
                    setNewAssignment((current) => ({
                      ...current,
                      assigned_role: event.target.value,
                    }))
                  }
                  className="w-full rounded-2xl border border-slate-700 bg-slate-900 p-3 text-sm text-white outline-none focus:border-cyan-400"
                >
                  <option value="Attorney">Attorney</option>
                  <option value="Paralegal">Paralegal</option>
                  <option value="Matter Team">Matter Team</option>
                  <option value="Reviewer">Reviewer</option>
                </select>

                <button
                  type="button"
                  onClick={() => void assignMatter()}
                  disabled={isLoading || !newAssignment.matter_id}
                  className="w-full rounded-2xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Assign Matter
                </button>
              </div>
            </Section>
          </div>

          <div className="min-w-0 space-y-6">
            <Section title="All Matters">
              <div className="mb-4 flex justify-end">
                <button
                  type="button"
                  onClick={() => void loadAdminData()}
                  className="rounded-xl border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-cyan-400 hover:text-cyan-300"
                >
                  Refresh
                </button>
              </div>

              {isLoading ? (
                <p className="text-slate-400">Loading admin data...</p>
              ) : matters.length === 0 ? (
                <p className="text-slate-400">No matters found.</p>
              ) : (
                <div className="space-y-3">
                  {matters.map((matter) => (
                    <div
                      key={matter.matter_id}
                      className="rounded-2xl border border-slate-800 bg-slate-900 p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-white">
                            {matter.matter_name}
                          </p>
                          <p className="mt-1 text-sm text-cyan-300">
                            {matter.client_name}
                          </p>
                        </div>
                        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
                          {matter.status}
                        </span>
                      </div>

                      <p className="mt-3 text-sm text-slate-300">
                        {matter.description}
                      </p>

                      <div className="mt-3 grid gap-2 md:grid-cols-2">
                        <Pill label="Matter ID" value={matter.matter_id} />
                        <Pill label="Type" value={matter.matter_type} />
                        <Pill
                          label="Primary Document"
                          value={matter.primary_document}
                        />
                        <Pill label="Created By" value={matter.created_by} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            <Section title="Matter Assignments">
              {assignments.length === 0 ? (
                <p className="text-slate-400">No assignments found.</p>
              ) : (
                <div className="space-y-3">
                  {assignments.map((assignment) => {
                    const matter = matters.find(
                      (item) => item.matter_id === assignment.matter_id
                    );

                    return (
                      <div
                        key={assignment.assignment_id}
                        className="rounded-2xl border border-slate-800 bg-slate-900 p-4"
                      >
                        <p className="font-semibold text-white">
                          {assignment.user_email}
                        </p>
                        <p className="mt-1 text-sm text-cyan-300">
                          {matter?.matter_name ?? assignment.matter_id}
                        </p>
                        <div className="mt-3 grid gap-2 md:grid-cols-3">
                          <Pill
                            label="Assigned Role"
                            value={assignment.assigned_role}
                          />
                          <Pill
                            label="Assigned By"
                            value={assignment.assigned_by}
                          />
                          <Pill
                            label="Assigned At"
                            value={assignment.assigned_at}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </Section>
          </div>
        </div>
      </div>
    </main>
  );
}
