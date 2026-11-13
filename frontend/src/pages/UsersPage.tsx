import React, { useEffect, useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import {
  UserPlus,
  Edit2,
  UserX,
  Building,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { DataTable } from "@/components/shared/DataTable";
import { FilterBar } from "@/components/shared/FilterBar";
import { ConfirmDialog } from "@/components/shared/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { Department, Role, User } from "@/types";
import { formatDate } from "@/lib/formatters";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export const UsersPage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  // Create User Modal State
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createFormData, setCreateFormData] = useState({
    full_name: "",
    email: "",
    password: "",
    role_id: "",
    department_id: "",
  });

  // Edit User Modal State
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editFormData, setEditFormData] = useState({
    full_name: "",
    role_id: "",
    department_id: "",
    is_active: true,
    password: "",
  });

  // Deactivate Confirm State
  const [deactivateModalOpen, setDeactivateModalOpen] = useState(false);
  const [userToDeactivate, setUserToDeactivate] = useState<User | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [usersList, rolesList, deptsList] = await Promise.all([
        api.get<User[]>("/users"),
        api.get<Role[]>("/users/roles"),
        api.get<Department[]>("/departments"),
      ]);
      setUsers(usersList);
      setRoles(rolesList);
      setDepartments(deptsList);
      if (rolesList.length > 0 && !createFormData.role_id) {
        setCreateFormData((prev) => ({ ...prev, role_id: rolesList[0].id }));
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to load user administration records.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/users", createFormData);
      toast.success(`User ${createFormData.full_name} created successfully.`);
      setCreateModalOpen(false);
      setCreateFormData({
        full_name: "",
        email: "",
        password: "",
        role_id: roles[0]?.id || "",
        department_id: "",
      });
      loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to create user.");
    }
  };

  const handleOpenEdit = (user: User) => {
    setEditingUser(user);
    setEditFormData({
      full_name: user.full_name,
      role_id: user.role_id,
      department_id: user.department_id || "",
      is_active: user.is_active,
      password: "",
    });
    setEditModalOpen(true);
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      const payload: any = {
        full_name: editFormData.full_name,
        role_id: editFormData.role_id,
        department_id: editFormData.department_id || null,
        is_active: editFormData.is_active,
      };
      if (editFormData.password) {
        payload.password = editFormData.password;
      }
      await api.put(`/users/${editingUser.id}`, payload);
      toast.success("User updated successfully.");
      setEditModalOpen(false);
      loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to update user.");
    }
  };

  const handleConfirmDeactivate = async () => {
    if (!userToDeactivate) return;
    try {
      await api.delete(`/users/${userToDeactivate.id}`);
      toast.success(`User ${userToDeactivate.full_name} deactivated.`);
      setDeactivateModalOpen(false);
      loadData();
    } catch (err: any) {
      toast.error(err.message || "Failed to deactivate user.");
    }
  };

  // Filter users by query
  const filteredUsers = users.filter((u) => {
    const q = searchQuery.toLowerCase();
    return (
      u.full_name.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q) ||
      u.role?.name.toLowerCase().includes(q) ||
      u.department?.name.toLowerCase().includes(q)
    );
  });

  const columns: ColumnDef<User>[] = [
    {
      accessorKey: "full_name",
      header: "User Details",
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="font-semibold text-foreground">
            {row.original.full_name}
          </span>
          <span className="text-xs text-muted-foreground font-mono">{row.original.email}</span>
        </div>
      ),
    },
    {
      accessorKey: "role",
      header: "Assigned Role",
      cell: ({ row }) => {
        const role = row.original.role;
        return (
          <Badge variant="outline" className="text-xs font-mono">
            {role?.name || "Auditor"}
          </Badge>
        );
      },
    },
    {
      accessorKey: "department",
      header: "Department / Local Body",
      cell: ({ row }) => {
        const dept = row.original.department;
        return (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Building className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="truncate max-w-[220px]">{dept?.name || "State Audit Pool"}</span>
          </div>
        );
      },
    },
    {
      accessorKey: "is_active",
      header: "Status",
      cell: ({ row }) => {
        const active = row.original.is_active;
        return (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
              active
                ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/25 dark:text-emerald-300"
                : "bg-muted text-muted-foreground border-border"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full mr-1.5 ${active ? "bg-emerald-500" : "bg-muted-foreground"}`}
            />
            {active ? "Active" : "Deactivated"}
          </span>
        );
      },
    },
    {
      accessorKey: "created_at",
      header: "Enrolled On",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground font-mono tabular-nums">
          {formatDate(row.original.created_at)}
        </span>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => {
        const isSelf = row.original.id === currentUser?.id;
        return (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleOpenEdit(row.original)}
              className="h-7 px-2 text-xs gap-1"
            >
              <Edit2 className="h-3 w-3" />
              Edit
            </Button>
            {!isSelf && row.original.is_active && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setUserToDeactivate(row.original);
                  setDeactivateModalOpen(true);
                }}
                className="h-7 px-2 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <UserX className="h-3 w-3" />
                Deactivate
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Administration"
        description="Manage departmental auditor accounts, RBAC permission roles, and unit assignments."
        badge={
          <Badge variant="outline" className="text-xs font-mono border-primary/30 text-primary">
            Administrator Access Only
          </Badge>
        }
      >
        <Button onClick={() => setCreateModalOpen(true)} className="gap-2">
          <UserPlus className="h-4 w-4" />
          Enroll New Auditor
        </Button>
      </PageHeader>

      <FilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        placeholder="Filter by name, email, role, or local body..."
        onReset={() => setSearchQuery("")}
      />

      <DataTable
        columns={columns}
        data={filteredUsers}
        isLoading={isLoading}
        emptyMessage="No departmental users found matching filter."
      />

      {/* Create User Dialog */}
      <Dialog open={createModalOpen} onOpenChange={setCreateModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Enroll New Departmental User</DialogTitle>
            <DialogDescription>
              Create an authenticated auditor or administrator account.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateUser} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Full Name</label>
              <Input
                placeholder="e.g. Anand Rao"
                value={createFormData.full_name}
                onChange={(e) => setCreateFormData({ ...createFormData, full_name: e.target.value })}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Official Email</label>
              <Input
                type="email"
                placeholder="anand@stateaudit.kar.gov.in"
                value={createFormData.email}
                onChange={(e) => setCreateFormData({ ...createFormData, email: e.target.value })}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Initial Password</label>
              <Input
                type="password"
                placeholder="Minimum 8 characters"
                value={createFormData.password}
                onChange={(e) => setCreateFormData({ ...createFormData, password: e.target.value })}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Departmental Role</label>
              <select
                className="w-full h-9 rounded-lg border border-input bg-background text-foreground px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={createFormData.role_id}
                onChange={(e) => setCreateFormData({ ...createFormData, role_id: e.target.value })}
                required
              >
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.code})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Assigned Unit / Zilla Panchayat</label>
              <select
                className="w-full h-9 rounded-lg border border-input bg-background text-foreground px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={createFormData.department_id}
                onChange={(e) => setCreateFormData({ ...createFormData, department_id: e.target.value })}
              >
                <option value="">Unassigned (General Pool)</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.type})
                  </option>
                ))}
              </select>
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setCreateModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">Create User Account</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit User Profile & Role</DialogTitle>
            <DialogDescription>
              Update auditor details, change RBAC role, or reset password.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleUpdateUser} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Full Name</label>
              <Input
                value={editFormData.full_name}
                onChange={(e) => setEditFormData({ ...editFormData, full_name: e.target.value })}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Assigned Role</label>
              <select
                className="w-full h-9 rounded-lg border border-input bg-background text-foreground px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={editFormData.role_id}
                onChange={(e) => setEditFormData({ ...editFormData, role_id: e.target.value })}
                required
              >
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Unit / Department</label>
              <select
                className="w-full h-9 rounded-lg border border-input bg-background text-foreground px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={editFormData.department_id}
                onChange={(e) => setEditFormData({ ...editFormData, department_id: e.target.value })}
              >
                <option value="">Unassigned (General Pool)</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.type})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Reset Password (Optional)</label>
              <Input
                type="password"
                placeholder="Leave blank to keep unchanged"
                value={editFormData.password}
                onChange={(e) => setEditFormData({ ...editFormData, password: e.target.value })}
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="is_active_check"
                checked={editFormData.is_active}
                onChange={(e) => setEditFormData({ ...editFormData, is_active: e.target.checked })}
                className="h-4 w-4 rounded border-input text-primary focus:ring-ring"
              />
              <label htmlFor="is_active_check" className="text-xs font-medium cursor-pointer">
                Account Active
              </label>
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setEditModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">Save Changes</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Deactivate User Confirmation */}
      <ConfirmDialog
        open={deactivateModalOpen}
        onOpenChange={setDeactivateModalOpen}
        title="Deactivate Auditor Account"
        description={`Are you sure you want to deactivate ${userToDeactivate?.full_name}? The user will be immediately logged out and unable to access the audit system until reactivated.`}
        confirmLabel="Deactivate Account"
        variant="destructive"
        onConfirm={handleConfirmDeactivate}
      />
    </div>
  );
};
