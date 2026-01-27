"use client";

/**
 * Admin Dashboard - Manual Resolution Queue
 *
 * Features:
 * - Real-time queue display with SLA countdown
 * - Status filtering (pending, in_progress, resolved, escalated)
 * - Priority sorting (SLA urgency, created_at, sla_deadline)
 * - Quick actions: resolve, regenerate PDF, refund
 * - Auto-refresh every 30 seconds
 * - Pending count badge
 * - SLA breached count badge
 *
 * Authentication:
 * - Requires X-API-Key header (ADMIN_API_KEY env var)
 * - IP whitelist check (ADMIN_IP_WHITELIST env var)
 *
 * Functional Requirement: FR-M-005 (Admin dashboard)
 * Reference: tasks.md T127I
 */

import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { AlertCircle, CheckCircle, Clock, RefreshCw, FileText, DollarSign } from "lucide-react";

// Types
interface ManualResolutionEntry {
  id: string;
  payment_id: string;
  user_email: string;
  normalized_email: string;
  issue_type: string;
  status: string;
  sla_deadline: string;
  hours_until_sla_breach: number;
  created_at: string;
  resolved_at: string | null;
  assigned_to: string | null;
  resolution_notes: string | null;
}

interface ManualResolutionListResponse {
  entries: ManualResolutionEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  pending_count: number;
  sla_breached_count: number;
}

export default function AdminManualResolutionDashboard() {
  const { toast } = useToast();

  // State
  const [apiKey, setApiKey] = useState<string>("");
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [data, setData] = useState<ManualResolutionListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("sla_deadline");
  const [sortOrder, setSortOrder] = useState<string>("asc");
  const [page, setPage] = useState<number>(1);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  // Dialog state for resolve action
  const [resolveDialogOpen, setResolveDialogOpen] = useState<boolean>(false);
  const [selectedEntry, setSelectedEntry] = useState<ManualResolutionEntry | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState<string>("");
  const [assignedTo, setAssignedTo] = useState<string>("");

  // Fetch manual resolution entries
  const fetchEntries = useCallback(async () => {
    if (!isAuthenticated || !apiKey) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: "10",
        sort_by: sortBy,
        sort_order: sortOrder,
      });

      if (statusFilter !== "all") {
        params.append("status_filter", statusFilter);
      }

      const response = await fetch(
        `/api/v1/admin/manual-resolution?${params.toString()}`,
        {
          headers: {
            "X-API-Key": apiKey,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const responseData: ManualResolutionListResponse = await response.json();
      setData(responseData);
    } catch (error) {
      console.error("Failed to fetch manual resolution entries:", error);
      toast({
        title: "Error",
        description: "Failed to fetch manual resolution entries",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, apiKey, page, sortBy, sortOrder, statusFilter, toast]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (autoRefresh && isAuthenticated) {
      fetchEntries();
      const interval = setInterval(fetchEntries, 30000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, isAuthenticated, fetchEntries]);

  // Initial fetch on authentication
  useEffect(() => {
    if (isAuthenticated) {
      fetchEntries();
    }
  }, [isAuthenticated, page, sortBy, sortOrder, statusFilter, fetchEntries]);

  // Authenticate with API key
  const handleAuthenticate = () => {
    if (apiKey.length < 32) {
      toast({
        title: "Invalid API Key",
        description: "API key must be at least 32 characters",
        variant: "destructive",
      });
      return;
    }
    setIsAuthenticated(true);
    toast({
      title: "Authenticated",
      description: "Successfully authenticated with admin API key",
    });
  };

  // Quick action: Resolve
  const handleResolve = async () => {
    if (!selectedEntry || !resolutionNotes.trim()) {
      toast({
        title: "Validation Error",
        description: "Resolution notes are required",
        variant: "destructive",
      });
      return;
    }

    try {
      const response = await fetch(
        `/api/v1/admin/manual-resolution/${selectedEntry.id}/resolve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey,
          },
          body: JSON.stringify({
            assigned_to: assignedTo || null,
            resolution_notes: resolutionNotes,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      toast({
        title: "Success",
        description: `Entry ${selectedEntry.id} marked as resolved`,
      });

      setResolveDialogOpen(false);
      setSelectedEntry(null);
      setResolutionNotes("");
      setAssignedTo("");
      fetchEntries();
    } catch (error) {
      console.error("Failed to resolve entry:", error);
      toast({
        title: "Error",
        description: "Failed to resolve entry",
        variant: "destructive",
      });
    }
  };

  // Quick action: Regenerate PDF
  const handleRegeneratePdf = async (entry: ManualResolutionEntry) => {
    try {
      const response = await fetch(
        `/api/v1/admin/manual-resolution/${entry.id}/regenerate`,
        {
          method: "POST",
          headers: {
            "X-API-Key": apiKey,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      toast({
        title: "Success",
        description: `PDF regeneration triggered for ${entry.id}`,
      });

      fetchEntries();
    } catch (error) {
      console.error("Failed to regenerate PDF:", error);
      toast({
        title: "Error",
        description: "Failed to trigger PDF regeneration",
        variant: "destructive",
      });
    }
  };

  // Quick action: Refund
  const handleRefund = async (entry: ManualResolutionEntry) => {
    if (!confirm(`Issue refund for payment ${entry.payment_id}?`)) {
      return;
    }

    try {
      const response = await fetch(
        `/api/v1/admin/manual-resolution/${entry.id}/refund`,
        {
          method: "POST",
          headers: {
            "X-API-Key": apiKey,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      toast({
        title: "Success",
        description: `Refund issued for ${entry.payment_id}`,
      });

      fetchEntries();
    } catch (error) {
      console.error("Failed to issue refund:", error);
      toast({
        title: "Error",
        description: "Failed to issue refund",
        variant: "destructive",
      });
    }
  };

  // Format hours until SLA breach
  const formatSlaCountdown = (hours: number): string => {
    if (hours < 0) {
      return `BREACHED ${Math.abs(hours).toFixed(1)}h ago`;
    }
    return `${hours.toFixed(1)}h remaining`;
  };

  // Get status badge color
  const getStatusBadgeVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (status) {
      case "pending":
        return "default";
      case "in_progress":
        return "secondary";
      case "resolved":
        return "outline";
      case "escalated":
        return "destructive";
      case "sla_missed_refunded":
        return "destructive";
      default:
        return "default";
    }
  };

  // Authentication screen
  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Admin Authentication</CardTitle>
            <CardDescription>
              Enter your admin API key to access the manual resolution dashboard
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="apiKey">Admin API Key</Label>
              <Input
                id="apiKey"
                type="password"
                placeholder="Enter admin API key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleAuthenticate();
                  }
                }}
              />
            </div>
            <Button onClick={handleAuthenticate} className="w-full">
              Authenticate
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Dashboard screen
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Manual Resolution Queue</h1>
            <p className="text-gray-500">Monitor and resolve failed operations</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={data && data.sla_breached_count > 0 ? "destructive" : "outline"}>
              <AlertCircle className="mr-1 h-4 w-4" />
              {data?.sla_breached_count || 0} SLA Breached
            </Badge>
            <Badge variant="default">
              <Clock className="mr-1 h-4 w-4" />
              {data?.pending_count || 0} Pending
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchEntries()}
              disabled={loading}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <Label>Status</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="escalated">Escalated</SelectItem>
                  <SelectItem value="sla_missed_refunded">SLA Missed (Refunded)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1 min-w-[200px]">
              <Label>Sort By</Label>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger>
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="priority">Priority (SLA Urgency)</SelectItem>
                  <SelectItem value="created_at">Created At</SelectItem>
                  <SelectItem value="sla_deadline">SLA Deadline</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1 min-w-[200px]">
              <Label>Sort Order</Label>
              <Select value={sortOrder} onValueChange={setSortOrder}>
                <SelectTrigger>
                  <SelectValue placeholder="Sort order" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="asc">Ascending</SelectItem>
                  <SelectItem value="desc">Descending</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Table */}
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Payment ID</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Issue Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>SLA Countdown</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8">
                      Loading...
                    </TableCell>
                  </TableRow>
                )}
                {!loading && data && data.entries.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                      No manual resolution entries found
                    </TableCell>
                  </TableRow>
                )}
                {!loading &&
                  data &&
                  data.entries.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="font-mono text-sm">{entry.payment_id}</TableCell>
                      <TableCell>{entry.user_email}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{entry.issue_type}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusBadgeVariant(entry.status)}>
                          {entry.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span
                          className={
                            entry.hours_until_sla_breach < 0
                              ? "text-red-600 font-semibold"
                              : entry.hours_until_sla_breach < 1
                              ? "text-orange-600 font-semibold"
                              : "text-gray-700"
                          }
                        >
                          {formatSlaCountdown(entry.hours_until_sla_breach)}
                        </span>
                      </TableCell>
                      <TableCell>
                        {new Date(entry.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedEntry(entry);
                              setResolveDialogOpen(true);
                            }}
                            disabled={entry.status === "resolved"}
                          >
                            <CheckCircle className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRegeneratePdf(entry)}
                            disabled={entry.status === "resolved"}
                          >
                            <FileText className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRefund(entry)}
                            disabled={entry.status === "sla_missed_refunded"}
                          >
                            <DollarSign className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex justify-center gap-2">
            <Button
              variant="outline"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <span className="flex items-center px-4">
              Page {page} of {data.total_pages}
            </span>
            <Button
              variant="outline"
              onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              disabled={page === data.total_pages}
            >
              Next
            </Button>
          </div>
        )}
      </div>

      {/* Resolve Dialog */}
      <Dialog open={resolveDialogOpen} onOpenChange={setResolveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve Manual Resolution Entry</DialogTitle>
            <DialogDescription>
              Mark this entry as resolved and add resolution notes
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="assignedTo">Assigned To (Optional)</Label>
              <Input
                id="assignedTo"
                placeholder="admin@ketomealplan.com"
                value={assignedTo}
                onChange={(e) => setAssignedTo(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="resolutionNotes">Resolution Notes *</Label>
              <Textarea
                id="resolutionNotes"
                placeholder="Describe how this issue was resolved..."
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResolveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleResolve}>Mark as Resolved</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
