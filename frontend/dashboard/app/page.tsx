"use client";

import {
  Activity,
  Bell,
  CalendarDays,
  CheckCircle2,
  Compass,
  Database,
  ExternalLink,
  Pause,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Save,
  Search,
  Send,
  ShieldCheck,
  TrendingUp,
  Trash2,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

const LOCAL_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const DEPLOYED_API_PROXY_BASE_URL = "/api/backend";
const AUTO_REFRESH_INTERVAL_MS = 30_000;
const REFRESH_COUNTDOWN_INTERVAL_MS = 1_000;

function getApiBaseUrl() {
  if (typeof window === "undefined") {
    return LOCAL_API_BASE_URL;
  }

  const localHosts = new Set(["localhost", "127.0.0.1", "::1"]);
  if (localHosts.has(window.location.hostname)) {
    return LOCAL_API_BASE_URL;
  }

  return DEPLOYED_API_PROXY_BASE_URL;
}

type WatchPriority = "high" | "normal" | "low";
type TestAlertChannel = "email" | "sms" | "both";
type AlertDeliveryFilter =
  | "all"
  | "sent"
  | "needs_retry"
  | "email_failed"
  | "sms_failed";

type Watch = {
  watch_id: string;
  status: "active" | "paused";
  park_name: string;
  facility_id: string | null;
  campground_name: string | null;
  date_start: string;
  date_end: string;
  camp_type: string;
  min_nights: number;
  notification_type: "email" | "sms" | "both" | "push";
  priority: WatchPriority;
  email_address: string | null;
  phone_number_masked: string | null;
  check_interval_seconds: number;
  last_checked_at: string | null;
};

type BatchWatchResponse = {
  created: { watch_id: string }[];
  skipped_duplicates: { existing_watch_id: string; campground_name: string | null }[];
};

type Alert = {
  alert_id: string;
  watch_id: string;
  park_name: string;
  message: string;
  reservation_url: string;
  created_at: string;
  campground_name: string | null;
  facility_id: string | null;
  campsite_id: string | null;
  site: string | null;
  available_date: string | null;
  available_end_date: string | null;
  nights: number | null;
  site_type: string | null;
  deliveries: { channel: string; status: string; detail: string }[];
};

type Campground = {
  facility_id: string;
  name: string;
  park_name: string;
  city: string | null;
  state_code: string | null;
  reservation_url: string;
};

type ParkSuggestion = {
  recarea_id: string;
  name: string;
  state_code: string | null;
  campgrounds_count: number;
};

type SchedulerJob = {
  job_id: string;
  next_run_time: string | null;
};

type IntegrationStatus = {
  configured: boolean;
  recipient: string | null;
  provider: string | null;
  detail: string;
};

type SettingsStatus = {
  environment: string;
  store: string;
  poll_interval_seconds: number;
  api_auth_configured: boolean;
  recreation_gov_base_url: string;
  ridb_api_configured: boolean;
  email: IntegrationStatus;
  sms: IntegrationStatus;
};

type TestAlertResponse = {
  message: string;
  deliveries: { channel: string; status: string; detail: string }[];
  cooldown_seconds: number;
};

type NextAvailability = {
  park_name: string;
  campground_name: string;
  facility_id: string;
  available_date: string;
  available_end_date: string;
  nights: number;
  site_count: number;
  site_types: string[];
  reservation_url: string;
};

type StrategyRecommendation = {
  recommendation_id: string;
  watch_id: string;
  match_type: "exact_match" | "same_park" | "flexible_date";
  park_name: string;
  campground_name: string;
  facility_id: string;
  available_date: string;
  available_end_date: string;
  nights: number;
  site_count: number;
  site_types: string[];
  reason: string;
  score: number;
  reservation_url: string;
};

type ReservationCheckLog = {
  log_id: string;
  watch_id: string;
  checked_at: string;
  status: "success" | "failed";
  result_count: number;
  alert_created: boolean;
  error_message: string | null;
  top_match_summary: string | null;
};

type BookingIntentStatus =
  | "created"
  | "opened"
  | "user_confirmed"
  | "abandoned";

type BookingIntent = {
  booking_intent_id: string;
  alert_id: string;
  watch_id: string;
  status: BookingIntentStatus;
  handoff_url: string;
  created_at: string;
  updated_at: string;
  park_name: string;
  campground_name: string | null;
  facility_id: string | null;
  campsite_id: string | null;
  site: string | null;
  available_date: string | null;
  available_end_date: string | null;
  nights: number | null;
  site_type: string | null;
  note: string;
};

type WatchEditDraft = {
  date_start: string;
  date_end: string;
  camp_type: string;
  min_nights: number;
  notification_type: Watch["notification_type"];
  priority: WatchPriority;
  email_address: string;
  phone_number: string;
};

type WatchGroup = {
  key: string;
  parkName: string;
  dateStart: string;
  dateEnd: string;
  campType: string;
  minNights: number;
  notificationType: Watch["notification_type"];
  priority: WatchPriority;
  checkIntervalSeconds: number;
  watches: Watch[];
  activeCount: number;
  pausedCount: number;
  status: Watch["status"] | "mixed";
  nextCheckAt: string | null;
  alertCount: number;
  latestAlertAt: string | null;
};

type WatchAnalyticsItem = {
  watchId: string;
  label: string;
  parkName: string;
  alertCount: number;
  latestAlertAt: string | null;
  latestOpening: string | null;
};

type DeleteTarget =
  | {
      type: "watch";
      watch: Watch;
    }
  | {
      type: "group";
      group: WatchGroup;
    };

export default function Dashboard() {
  const [watches, setWatches] = useState<Watch[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [checkLogs, setCheckLogs] = useState<ReservationCheckLog[]>([]);
  const [bookingIntents, setBookingIntents] = useState<BookingIntent[]>([]);
  const [alertWatchFilter, setAlertWatchFilter] = useState("all");
  const [alertDeliveryFilter, setAlertDeliveryFilter] =
    useState<AlertDeliveryFilter>("all");
  const [jobs, setJobs] = useState<SchedulerJob[]>([]);
  const [settingsStatus, setSettingsStatus] = useState<SettingsStatus | null>(null);
  const [dbStore, setDbStore] = useState("checking");
  const [nextOpenings, setNextOpenings] = useState<Record<string, NextAvailability[]>>(
    {},
  );
  const [nextLoadingWatch, setNextLoadingWatch] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<
    Record<string, StrategyRecommendation[]>
  >({});
  const [recommendationLoadingKey, setRecommendationLoadingKey] = useState<
    string | null
  >(null);
  const [editingWatchId, setEditingWatchId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<WatchEditDraft | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [campgrounds, setCampgrounds] = useState<Campground[]>([]);
  const [parkSuggestions, setParkSuggestions] = useState<ParkSuggestion[]>([]);
  const [showParkSuggestions, setShowParkSuggestions] = useState(false);
  const [parkLoading, setParkLoading] = useState(false);
  const [selectedCampgroundIds, setSelectedCampgroundIds] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [dateStart, setDateStart] = useState("2026-05-10");
  const [dateEnd, setDateEnd] = useState("2026-05-12");
  const [campType, setCampType] = useState("any");
  const [minNights, setMinNights] = useState(1);
  const [notificationType, setNotificationType] = useState("both");
  const [watchPriority, setWatchPriority] = useState<WatchPriority>("normal");
  const [alertEmail, setAlertEmail] = useState("");
  const [alertPhone, setAlertPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [testAlertBusy, setTestAlertBusy] = useState<TestAlertChannel | null>(
    null,
  );
  const [retryingAlertId, setRetryingAlertId] = useState<string | null>(null);
  const [bookingIntentBusyAlertId, setBookingIntentBusyAlertId] = useState<
    string | null
  >(null);
  const [bookingStatusBusyId, setBookingStatusBusyId] = useState<string | null>(
    null,
  );
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [nextRefreshAt, setNextRefreshAt] = useState<string | null>(null);
  const [clockNow, setClockNow] = useState(() => Date.now());
  const [notice, setNotice] = useState("");

  const activeCount = useMemo(
    () => watches.filter((watch) => watch.status === "active").length,
    [watches],
  );
  const notificationsConfigured = Boolean(
    settingsStatus?.email.configured || settingsStatus?.sms.configured,
  );
  const filteredAlerts = useMemo(() => {
    const watchFilteredAlerts =
      alertWatchFilter === "all"
        ? alerts
        : alerts.filter((alert) => alert.watch_id === alertWatchFilter);
    const visible = watchFilteredAlerts.filter((alert) =>
      alertMatchesDeliveryFilter(alert, alertDeliveryFilter),
    );

    return [...visible].sort(
      (left, right) =>
        new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
    );
  }, [alertDeliveryFilter, alertWatchFilter, alerts]);
  const deliveryHealth = useMemo(() => {
    let sentDeliveries = 0;
    let totalDeliveries = 0;
    let emailFailures = 0;
    let smsFailures = 0;
    let retryAlertCount = 0;
    let lastSuccessfulDeliveryAt: string | null = null;

    alerts.forEach((alert) => {
      if (hasRetryableDelivery(alert)) {
        retryAlertCount += 1;
      }

      alert.deliveries.forEach((delivery) => {
        totalDeliveries += 1;

        if (delivery.status === "sent") {
          sentDeliveries += 1;
          if (
            !lastSuccessfulDeliveryAt ||
            new Date(alert.created_at).getTime() >
              new Date(lastSuccessfulDeliveryAt).getTime()
          ) {
            lastSuccessfulDeliveryAt = alert.created_at;
          }
          return;
        }

        if (isFailedDelivery(delivery)) {
          if (delivery.channel === "email") {
            emailFailures += 1;
          }
          if (delivery.channel === "sms") {
            smsFailures += 1;
          }
        }
      });
    });

    const successRate = totalDeliveries
      ? Math.round((sentDeliveries / totalDeliveries) * 100)
      : null;

    return {
      emailFailures,
      lastSuccessfulDeliveryAt,
      metricLabel: successRate === null ? "n/a" : `${successRate}%`,
      retryAlertCount,
      sentDeliveries,
      smsFailures,
      successRate,
      totalDeliveries,
    };
  }, [alerts]);
  const alertsByWatchId = useMemo(() => {
    return [...alerts]
      .sort(
        (left, right) =>
          new Date(right.created_at).getTime() -
          new Date(left.created_at).getTime(),
      )
      .reduce<Record<string, Alert[]>>((groupedAlerts, alert) => {
        groupedAlerts[alert.watch_id] = groupedAlerts[alert.watch_id] ?? [];
        groupedAlerts[alert.watch_id].push(alert);
        return groupedAlerts;
      }, {});
  }, [alerts]);
  const checkLogsByWatchId = useMemo(() => {
    return [...checkLogs]
      .sort(
        (left, right) =>
          new Date(right.checked_at).getTime() -
          new Date(left.checked_at).getTime(),
      )
      .reduce<Record<string, ReservationCheckLog[]>>((groupedLogs, log) => {
        groupedLogs[log.watch_id] = groupedLogs[log.watch_id] ?? [];
        groupedLogs[log.watch_id].push(log);
        return groupedLogs;
      }, {});
  }, [checkLogs]);
  const failedCheckCount = useMemo(
    () => checkLogs.filter((log) => log.status === "failed").length,
    [checkLogs],
  );
  const watchLabelById = useMemo(() => {
    return watches.reduce<Record<string, string>>((labels, watch) => {
      labels[watch.watch_id] = watch.campground_name ?? watch.park_name;
      return labels;
    }, {});
  }, [watches]);
  const bookingIntentByAlertId = useMemo(() => {
    return bookingIntents.reduce<Record<string, BookingIntent>>(
      (intentsByAlertId, intent) => {
        intentsByAlertId[intent.alert_id] = intent;
        return intentsByAlertId;
      },
      {},
    );
  }, [bookingIntents]);
  const watchAnalytics = useMemo(() => {
    const watchItems = watches
      .map<WatchAnalyticsItem>((watch) => {
        const watchAlerts = alertsByWatchId[watch.watch_id] ?? [];
        const latestAlert = watchAlerts[0] ?? null;
        const latestOpening =
          latestAlert?.available_date && latestAlert.available_end_date
            ? `${latestAlert.available_date} to ${latestAlert.available_end_date}`
            : latestAlert?.available_date ?? null;

        return {
          watchId: watch.watch_id,
          label: watch.campground_name ?? watch.park_name,
          parkName: watch.park_name,
          alertCount: watchAlerts.length,
          latestAlertAt: latestAlert?.created_at ?? null,
          latestOpening,
        };
      })
      .sort(
        (left, right) =>
          right.alertCount - left.alertCount ||
          new Date(right.latestAlertAt ?? 0).getTime() -
            new Date(left.latestAlertAt ?? 0).getTime() ||
          left.label.localeCompare(right.label),
      );
    const topWatch = watchItems.find((item) => item.alertCount > 0) ?? null;
    const latestAlert =
      [...alerts].sort(
        (left, right) =>
          new Date(right.created_at).getTime() -
          new Date(left.created_at).getTime(),
      )[0] ?? null;

    return {
      hotWatches: watchItems.filter((item) => item.alertCount > 0).slice(0, 5),
      latestAlert,
      latestOpening:
        latestAlert?.available_date && latestAlert.available_end_date
          ? `${latestAlert.available_date} to ${latestAlert.available_end_date}`
          : latestAlert?.available_date ?? null,
      topWatch,
      totalOpenings: alerts.length,
      watchesWithOpenings: watchItems.filter((item) => item.alertCount > 0).length,
    };
  }, [alerts, alertsByWatchId, watches]);
  const nextCheckByWatchId = useMemo(() => {
    return jobs.reduce<Record<string, string | null>>((nextChecks, job) => {
      if (job.job_id.startsWith("watch:")) {
        nextChecks[job.job_id.replace("watch:", "")] = job.next_run_time;
      }
      return nextChecks;
    }, {});
  }, [jobs]);
  const secondsUntilNextRefresh = useMemo(() => {
    if (!nextRefreshAt) {
      return null;
    }

    return Math.max(
      0,
      Math.ceil((new Date(nextRefreshAt).getTime() - clockNow) / 1000),
    );
  }, [clockNow, nextRefreshAt]);
  const watchGroups = useMemo(() => {
    const groups = new Map<
      string,
      Omit<
        WatchGroup,
        "activeCount" | "pausedCount" | "status" | "nextCheckAt" | "alertCount" | "latestAlertAt"
      >
    >();
    const sortedWatches = [...watches].sort((left, right) => {
      const groupOrder =
        left.park_name.localeCompare(right.park_name) ||
        left.date_start.localeCompare(right.date_start) ||
        left.date_end.localeCompare(right.date_end) ||
        left.camp_type.localeCompare(right.camp_type) ||
        left.min_nights - right.min_nights ||
        left.notification_type.localeCompare(right.notification_type) ||
        prioritySortRank(left.priority) - prioritySortRank(right.priority);

      return (
        groupOrder ||
        (left.campground_name ?? left.park_name).localeCompare(
          right.campground_name ?? right.park_name,
        )
      );
    });

    sortedWatches.forEach((watch) => {
      const key = [
        watch.park_name,
        watch.date_start,
        watch.date_end,
        watch.camp_type,
        watch.min_nights,
        watch.notification_type,
        watch.priority,
      ].join("|");
      const group =
        groups.get(key) ??
        {
          key,
          parkName: watch.park_name,
          dateStart: watch.date_start,
          dateEnd: watch.date_end,
          campType: watch.camp_type,
          minNights: watch.min_nights,
          notificationType: watch.notification_type,
          priority: watch.priority,
          checkIntervalSeconds: watch.check_interval_seconds,
          watches: [],
        };

      group.watches.push(watch);
      groups.set(key, group);
    });

    return Array.from(groups.values()).map((group) => {
      const activeCount = group.watches.filter(
        (watch) => watch.status === "active",
      ).length;
      const pausedCount = group.watches.length - activeCount;
      const status: WatchGroup["status"] =
        activeCount === group.watches.length
          ? "active"
          : pausedCount === group.watches.length
            ? "paused"
            : "mixed";
      const nextCheckAt =
        group.watches
          .map((watch) => nextCheckByWatchId[watch.watch_id])
          .filter((nextRunTime): nextRunTime is string => Boolean(nextRunTime))
          .sort(
            (left, right) => new Date(left).getTime() - new Date(right).getTime(),
          )[0] ?? null;
      const groupAlerts = group.watches.flatMap(
        (watch) => alertsByWatchId[watch.watch_id] ?? [],
      );
      const latestAlertAt =
        groupAlerts
          .map((alert) => alert.created_at)
          .sort(
            (left, right) => new Date(right).getTime() - new Date(left).getTime(),
          )[0] ?? null;

      return {
        ...group,
        activeCount,
        pausedCount,
        status,
        nextCheckAt,
        alertCount: groupAlerts.length,
        latestAlertAt,
      };
    });
  }, [alertsByWatchId, nextCheckByWatchId, watches]);

  const fetchJson = useCallback(async function fetchJson<T>(
    path: string,
    init?: RequestInit,
  ): Promise<T> {
    const requestUrl = `${getApiBaseUrl()}${path}`;
    let response: Response;
    try {
      response = await fetch(requestUrl, init);
    } catch {
      throw new Error(`Could not reach backend at ${requestUrl}.`);
    }
    if (!response.ok) {
      const message = await response.text();
      throw new Error(parseApiError(message) || response.statusText);
    }
    return response.json();
  }, []);

  const refreshData = useCallback(async function refreshData() {
    const [
      watchData,
      alertData,
      checkLogData,
      bookingIntentData,
      jobData,
      settingsData,
    ] =
      await Promise.all([
        fetchJson<Watch[]>("/watches"),
        fetchJson<Alert[]>("/alerts"),
        fetchJson<ReservationCheckLog[]>("/check-logs?limit=100"),
        fetchJson<BookingIntent[]>("/booking-intents?limit=100"),
        fetchJson<SchedulerJob[]>("/scheduler/jobs"),
        fetchJson<SettingsStatus>("/settings/status"),
      ]);
    setWatches(
      watchData.map((watch) => ({
        ...watch,
        priority: watch.priority ?? "normal",
        check_interval_seconds:
          watch.check_interval_seconds ?? settingsData.poll_interval_seconds,
      })),
    );
    setAlerts(alertData);
    setCheckLogs(checkLogData);
    setBookingIntents(bookingIntentData);
    setJobs(jobData);
    setSettingsStatus(settingsData);
    setDbStore(settingsData.store);
    setLastRefreshedAt(new Date().toISOString());
  }, [fetchJson]);

  async function searchCampgrounds(event?: FormEvent, queryOverride?: string) {
    event?.preventDefault();
    setBusy(true);
    setNotice("");
    const query = queryOverride ?? searchQuery;
    try {
      const results = await fetchJson<Campground[]>(
        `/campgrounds/search?query=${encodeURIComponent(query)}&limit=8`,
      );
      setCampgrounds(results);
      setSelectedCampgroundIds(results[0] ? [results[0].facility_id] : []);
      setNotice(results.length ? "Campgrounds loaded." : "No campgrounds found.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Search failed.");
    } finally {
      setBusy(false);
    }
  }

  async function searchParks(query: string) {
    if (query.trim().length < 2) {
      setParkSuggestions([]);
      setShowParkSuggestions(false);
      return;
    }

    setParkLoading(true);
    try {
      const results = await fetchJson<ParkSuggestion[]>(
        `/parks/search?query=${encodeURIComponent(query)}&limit=8`,
      );
      setParkSuggestions(results);
      setShowParkSuggestions(true);
    } catch {
      setParkSuggestions([]);
      setShowParkSuggestions(false);
    } finally {
      setParkLoading(false);
    }
  }

  function selectParkSuggestion(park: ParkSuggestion) {
    setSearchQuery(park.name);
    setShowParkSuggestions(false);
    setParkSuggestions([]);
    searchCampgrounds(undefined, park.name).catch((error) => {
      setNotice(error instanceof Error ? error.message : "Campground search failed.");
    });
  }

  async function createWatch(event: FormEvent) {
    event.preventDefault();
    const selectedCampgrounds = campgrounds.filter((campground) =>
      selectedCampgroundIds.includes(campground.facility_id),
    );
    const emailAddress = alertEmail.trim() || undefined;
    const phoneNumber = alertPhone.trim() || undefined;

    if (!selectedCampgrounds.length) {
      setNotice("Select at least one campground first.");
      return;
    }

    setBusy(true);
    setNotice("");
    try {
      const response = await fetchJson<BatchWatchResponse>(
        "/watch-reservations/batch",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            watches: selectedCampgrounds.map((campground) => ({
              park_name: campground.park_name,
              facility_id: campground.facility_id,
              campground_name: campground.name,
              date_start: dateStart,
              date_end: dateEnd,
              camp_type: campType,
              min_nights: minNights,
              flexibility_days: 0,
              notification_type: notificationType,
              priority: watchPriority,
              email_address: emailAddress,
              phone_number: phoneNumber,
            })),
          }),
        },
      );
      const createdCount = response.created.length;
      const skippedCount = response.skipped_duplicates.length;
      const notices = [];
      if (createdCount) {
        notices.push(
          `Created ${createdCount} watch${createdCount === 1 ? "" : "es"}.`,
        );
      }
      if (skippedCount) {
        notices.push(
          `Skipped ${skippedCount} duplicate${skippedCount === 1 ? "" : "s"}.`,
        );
      }
      setNotice(notices.join(" ") || "No watches were created.");
      await refreshData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Create failed.");
    } finally {
      setBusy(false);
    }
  }

  function toggleCampground(facilityId: string) {
    setSelectedCampgroundIds((current) =>
      current.includes(facilityId)
        ? current.filter((id) => id !== facilityId)
        : [...current, facilityId],
    );
  }

  function clearCampgroundSearch() {
    setSelectedCampgroundIds([]);
    setSearchQuery("");
    setCampgrounds([]);
    setParkSuggestions([]);
    setShowParkSuggestions(false);
    setNotice("");
  }

  async function postAction(path: string) {
    setBusy(true);
    setNotice("");
    try {
      await fetchJson(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      await refreshData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function sendTestAlert(channel: TestAlertChannel) {
    setBusy(true);
    setTestAlertBusy(channel);
    setNotice("");
    try {
      const response = await fetchJson<TestAlertResponse>("/alerts/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notification_type: channel }),
      });
      const deliverySummary = response.deliveries
        .map(formatTestDelivery)
        .join("; ");
      setNotice(
        deliverySummary
          ? `Test alert attempted: ${deliverySummary}.`
          : response.message,
      );
      await refreshData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Test alert failed.");
    } finally {
      setTestAlertBusy(null);
      setBusy(false);
    }
  }

  async function retryAlertDelivery(alertId: string) {
    setBusy(true);
    setRetryingAlertId(alertId);
    setNotice("");
    try {
      const alert = await fetchJson<Alert>(`/alerts/${alertId}/retry-delivery`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const deliverySummary = alert.deliveries
        .map(formatTestDelivery)
        .join("; ");
      setNotice(
        deliverySummary
          ? `Delivery retry attempted: ${deliverySummary}.`
          : "No delivery retry was needed.",
      );
      await refreshData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Retry failed.");
    } finally {
      setRetryingAlertId(null);
      setBusy(false);
    }
  }

  async function startBookAssist(alert: Alert) {
    let bookingWindow: Window | null = null;
    if (typeof window !== "undefined") {
      bookingWindow = window.open("", "_blank");
      if (bookingWindow) {
        bookingWindow.opener = null;
      }
    }

    setBusy(true);
    setBookingIntentBusyAlertId(alert.alert_id);
    setNotice("");
    try {
      const bookingIntent = await fetchJson<BookingIntent>(
        `/alerts/${alert.alert_id}/book-assist`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );

      let updatedIntent = bookingIntent;
      if (bookingWindow) {
        bookingWindow.location.href = bookingIntent.handoff_url;
        if (bookingIntent.status !== "user_confirmed") {
          updatedIntent = await fetchJson<BookingIntent>(
            `/booking-intents/${bookingIntent.booking_intent_id}/opened`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
            },
          );
        }
      }

      setBookingIntents((current) =>
        upsertBookingIntent(current, updatedIntent),
      );
      setNotice(
        bookingWindow
          ? "Book Assist opened Recreation.gov. Confirm or abandon it here after checkout."
          : "Book Assist created. Pop-up was blocked; use the handoff link on this alert.",
      );
      await refreshData();
    } catch (error) {
      if (bookingWindow) {
        bookingWindow.close();
      }
      setNotice(error instanceof Error ? error.message : "Book Assist failed.");
    } finally {
      setBookingIntentBusyAlertId(null);
      setBusy(false);
    }
  }

  async function updateBookingIntentStatus(
    bookingIntentId: string,
    transition: "user-confirmed" | "abandoned",
  ) {
    setBusy(true);
    setBookingStatusBusyId(bookingIntentId);
    setNotice("");
    try {
      const bookingIntent = await fetchJson<BookingIntent>(
        `/booking-intents/${bookingIntentId}/${transition}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );
      setBookingIntents((current) =>
        upsertBookingIntent(current, bookingIntent),
      );
      setNotice(
        transition === "user-confirmed"
          ? "Booking intent marked as user confirmed."
          : "Booking intent marked as abandoned.",
      );
      await refreshData();
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Booking status update failed.",
      );
    } finally {
      setBookingStatusBusyId(null);
      setBusy(false);
    }
  }

  async function statusAction(path: string, watchId: string) {
    setBusy(true);
    setNotice("");
    try {
      await fetchJson(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ watch_id: watchId }),
      });
      await refreshData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function statusGroupAction(
    group: WatchGroup,
    status: Watch["status"],
    path: string,
    label: string,
  ) {
    const targetWatches = group.watches.filter((watch) => watch.status !== status);
    if (!targetWatches.length) {
      setNotice(`All watches in this group are already ${status}.`);
      return;
    }

    setBusy(true);
    setNotice("");
    try {
      await Promise.all(
        targetWatches.map((watch) =>
          fetchJson(path, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ watch_id: watch.watch_id }),
          }),
        ),
      );
      setNotice(
        `${label} ${targetWatches.length} watch${
          targetWatches.length === 1 ? "" : "es"
        }.`,
      );
      await refreshData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Group action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function checkGroupNow(group: WatchGroup) {
    const activeWatches = group.watches.filter((watch) => watch.status === "active");
    if (!activeWatches.length) {
      setNotice("Resume at least one watch in this group before checking now.");
      return;
    }

    setBusy(true);
    setNotice("");
    try {
      await Promise.all(
        activeWatches.map((watch) =>
          fetchJson(`/watches/${watch.watch_id}/check-now`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
          }),
        ),
      );
      setNotice(
        `Checked ${activeWatches.length} watch${
          activeWatches.length === 1 ? "" : "es"
        }.`,
      );
      await refreshData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Group check failed.");
    } finally {
      setBusy(false);
    }
  }

  function beginDeleteWatch(watch: Watch) {
    setDeleteTarget({ type: "watch", watch });
  }

  function beginDeleteGroup(group: WatchGroup) {
    setDeleteTarget({ type: "group", group });
  }

  function cancelDelete() {
    setDeleteTarget(null);
  }

  async function confirmDelete() {
    if (!deleteTarget) {
      return;
    }

    const watchesToDelete =
      deleteTarget.type === "watch"
        ? [deleteTarget.watch]
        : deleteTarget.group.watches;
    const watchIds = watchesToDelete.map((watch) => watch.watch_id);

    setBusy(true);
    setNotice("");
    try {
      await Promise.all(
        watchIds.map((watchId) =>
          fetchJson(`/watches/${watchId}`, { method: "DELETE" }),
        ),
      );
      setNextOpenings((current) => {
        const next = { ...current };
        watchIds.forEach((watchId) => {
          delete next[watchId];
        });
        return next;
      });
      if (editingWatchId && watchIds.includes(editingWatchId)) {
        cancelEdit();
      }
      if (watchIds.includes(alertWatchFilter)) {
        setAlertWatchFilter("all");
      }
      setDeleteTarget(null);
      setNotice(
        `Deleted ${watchIds.length} watch${watchIds.length === 1 ? "" : "es"}.`,
      );
      await refreshData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Delete failed.");
    } finally {
      setBusy(false);
    }
  }

  function beginEdit(watch: Watch) {
    setEditingWatchId(watch.watch_id);
    setEditDraft({
      date_start: watch.date_start,
      date_end: watch.date_end,
      camp_type: watch.camp_type,
      min_nights: watch.min_nights,
      notification_type: watch.notification_type,
      priority: watch.priority,
      email_address: watch.email_address ?? "",
      phone_number: "",
    });
  }

  function cancelEdit() {
    setEditingWatchId(null);
    setEditDraft(null);
  }

  async function saveWatchEdit(watchId: string) {
    if (!editDraft) {
      return;
    }

    if (editDraft.date_start > editDraft.date_end) {
      setNotice("Start date must be before or equal to end date.");
      return;
    }

    setBusy(true);
    setNotice("");
    try {
      const updatePayload = {
        ...editDraft,
        email_address: editDraft.email_address.trim() || undefined,
        phone_number: editDraft.phone_number.trim() || undefined,
      };
      await fetchJson(`/watches/${watchId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatePayload),
      });
      setNextOpenings((current) => {
        const next = { ...current };
        delete next[watchId];
        return next;
      });
      cancelEdit();
      setNotice("Watch updated.");
      await refreshData();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function findNextAvailable(watchId: string) {
    setNextLoadingWatch(watchId);
    setNotice("");
    try {
      const openings = await fetchJson<NextAvailability[]>(
        `/watches/${watchId}/next-available?days=90&limit=5`,
      );
      setNextOpenings((current) => ({ ...current, [watchId]: openings }));
      setNotice(
        openings.length
          ? "Next openings loaded."
          : "No openings found in the next 90 days.",
      );
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Lookup failed.");
    } finally {
      setNextLoadingWatch(null);
    }
  }

  async function findNextAvailableForGroup(group: WatchGroup) {
    const loadingKey = `group:${group.key}`;
    setBusy(true);
    setNextLoadingWatch(loadingKey);
    setNotice("");
    try {
      const results = await Promise.all(
        group.watches.map(async (watch) => ({
          watchId: watch.watch_id,
          openings: await fetchJson<NextAvailability[]>(
            `/watches/${watch.watch_id}/next-available?days=90&limit=5`,
          ),
        })),
      );

      setNextOpenings((current) => {
        const next = { ...current };
        results.forEach((result) => {
          next[result.watchId] = result.openings;
        });
        return next;
      });

      const openingCount = results.reduce(
        (count, result) => count + result.openings.length,
        0,
      );
      setNotice(
        openingCount
          ? `Loaded ${openingCount} opening${openingCount === 1 ? "" : "s"}.`
          : "No openings found for this group in the next 90 days.",
      );
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Group lookup failed.");
    } finally {
      setNextLoadingWatch(null);
      setBusy(false);
    }
  }

  async function loadRecommendationsForWatch(watchId: string) {
    setRecommendationLoadingKey(watchId);
    setNotice("");
    try {
      const watchRecommendations = await fetchJson<StrategyRecommendation[]>(
        `/watches/${watchId}/recommendations?days=90&limit=6`,
      );
      setRecommendations((current) => ({
        ...current,
        [watchId]: watchRecommendations,
      }));
      setNotice(
        watchRecommendations.length
          ? "Strategy recommendations loaded."
          : "No strategy recommendations found.",
      );
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Recommendation lookup failed.");
    } finally {
      setRecommendationLoadingKey(null);
    }
  }

  async function loadRecommendationsForGroup(group: WatchGroup) {
    const loadingKey = `group:${group.key}`;
    setBusy(true);
    setRecommendationLoadingKey(loadingKey);
    setNotice("");
    try {
      const results = await Promise.all(
        group.watches.map(async (watch) => ({
          watchId: watch.watch_id,
          recommendations: await fetchJson<StrategyRecommendation[]>(
            `/watches/${watch.watch_id}/recommendations?days=90&limit=6`,
          ),
        })),
      );

      setRecommendations((current) => {
        const next = { ...current };
        results.forEach((result) => {
          next[result.watchId] = result.recommendations;
        });
        return next;
      });

      const recommendationCount = results.reduce(
        (count, result) => count + result.recommendations.length,
        0,
      );
      setNotice(
        recommendationCount
          ? `Loaded ${recommendationCount} recommendation${
              recommendationCount === 1 ? "" : "s"
            }.`
          : "No strategy recommendations found for this group.",
      );
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Group recommendation lookup failed.");
    } finally {
      setRecommendationLoadingKey(null);
      setBusy(false);
    }
  }

  useEffect(() => {
    refreshData().catch((error) => {
      setNotice(error instanceof Error ? error.message : "Refresh failed.");
    });
    setNextRefreshAt(new Date(Date.now() + AUTO_REFRESH_INTERVAL_MS).toISOString());
    const intervalId = window.setInterval(() => {
      refreshData().catch(() => undefined);
      setNextRefreshAt(
        new Date(Date.now() + AUTO_REFRESH_INTERVAL_MS).toISOString(),
      );
    }, AUTO_REFRESH_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [refreshData]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      setClockNow(Date.now());
    }, REFRESH_COUNTDOWN_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      searchParks(searchQuery).catch(() => undefined);
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [searchQuery]);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">ParkReserve AI</p>
          <h1>Reservation Monitor</h1>
        </div>
        <div className="topbarActions">
          <div className="refreshMeta">
            {lastRefreshedAt ? (
              <span>Dashboard updated {formatDateTimeWithSeconds(lastRefreshedAt)}</span>
            ) : null}
            {secondsUntilNextRefresh !== null ? (
              <span>Dashboard refresh in {secondsUntilNextRefresh}s</span>
            ) : null}
          </div>
          <button className="iconButton" onClick={refreshData} disabled={busy}>
            <RefreshCw size={18} />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      <section className="metrics">
        <Metric icon={<CalendarDays size={18} />} label="Active Watches" value={activeCount} />
        <Metric icon={<Bell size={18} />} label="Alerts" value={alerts.length} />
        <Metric icon={<Activity size={18} />} label="Checks" value={checkLogs.length} />
        <Metric
          icon={<TrendingUp size={18} />}
          label="Hot Watches"
          value={watchAnalytics.watchesWithOpenings}
        />
        <Metric
          icon={<ShieldCheck size={18} />}
          label="Delivery Health"
          value={deliveryHealth.metricLabel}
        />
        <Metric icon={<Play size={18} />} label="Scheduled Jobs" value={jobs.length} />
        <Metric icon={<Database size={18} />} label="Store" value={dbStore} />
      </section>

      <section className="panel statusPanel">
        <div className="panelHeader">
          <h2>System Status</h2>
          <div className="panelHeaderActions">
            <span>{settingsStatus?.environment ?? "checking"}</span>
            <button
              className="iconButton"
              disabled={busy || Boolean(testAlertBusy) || !notificationsConfigured}
              onClick={() => sendTestAlert("email")}
              type="button"
            >
              <Send size={17} />
              <span>{testAlertBusy === "email" ? "Sending" : "Test Email"}</span>
            </button>
            <button
              className="iconButton"
              disabled={busy || Boolean(testAlertBusy) || !notificationsConfigured}
              onClick={() => sendTestAlert("sms")}
              type="button"
            >
              <Send size={17} />
              <span>{testAlertBusy === "sms" ? "Sending" : "Test SMS"}</span>
            </button>
          </div>
        </div>
        <div className="statusGrid">
          <StatusItem
            detail={
              settingsStatus?.email.configured
                ? settingsStatus.email.recipient
                : settingsStatus?.email.detail
            }
            label="Email"
            ok={settingsStatus?.email.configured}
            value={settingsStatus?.email.configured ? "configured" : "missing"}
          />
          <StatusItem
            detail={
              settingsStatus?.sms.configured
                ? settingsStatus.sms.recipient
                : settingsStatus?.sms.detail
            }
            label="SMS"
            ok={settingsStatus?.sms.configured}
            value={settingsStatus?.sms.configured ? "configured" : "missing"}
          />
          <StatusItem
            detail={settingsStatus ? `${settingsStatus.poll_interval_seconds}s` : undefined}
            label="Base check"
            ok={Boolean(settingsStatus)}
            value="normal priority"
          />
          <StatusItem
            detail={`${checkLogs.length} recent check${
              checkLogs.length === 1 ? "" : "s"
            }`}
            label="Check logs"
            ok={!failedCheckCount}
            value={failedCheckCount ? `${failedCheckCount} failed` : "healthy"}
          />
          <StatusItem
            detail={`${AUTO_REFRESH_INTERVAL_MS / 1000}s`}
            label="Refresh"
            ok
            value="dashboard"
          />
          <StatusItem
            detail={settingsStatus?.api_auth_configured ? "shared token set" : "local mode"}
            label="API auth"
            ok={Boolean(settingsStatus)}
            value={settingsStatus?.api_auth_configured ? "protected" : "optional"}
          />
          <StatusItem
            detail={settingsStatus?.ridb_api_configured ? "API key set" : "public search"}
            label="RIDB"
            ok={Boolean(settingsStatus)}
            value={settingsStatus?.ridb_api_configured ? "configured" : "optional"}
          />
        </div>
      </section>

      <section className="panel deliveryPanel">
        <div className="panelHeader">
          <h2>Delivery Health</h2>
          <span>
            {deliveryHealth.totalDeliveries
              ? `${deliveryHealth.sentDeliveries}/${deliveryHealth.totalDeliveries} sent`
              : "no deliveries yet"}
          </span>
        </div>
        <div className="healthGrid">
          <StatusItem
            detail={
              deliveryHealth.totalDeliveries
                ? `${deliveryHealth.sentDeliveries} sent of ${deliveryHealth.totalDeliveries}`
                : "waiting for first alert"
            }
            label="Success rate"
            ok={!deliveryHealth.retryAlertCount}
            value={deliveryHealth.metricLabel}
          />
          <StatusItem
            detail="failed or missing channels"
            label="Needs retry"
            ok={!deliveryHealth.retryAlertCount}
            value={`${deliveryHealth.retryAlertCount} alert${
              deliveryHealth.retryAlertCount === 1 ? "" : "s"
            }`}
          />
          <StatusItem
            detail={`${deliveryHealth.emailFailures} failed`}
            label="Email"
            ok={!deliveryHealth.emailFailures}
            value={deliveryHealth.emailFailures ? "attention" : "healthy"}
          />
          <StatusItem
            detail={`${deliveryHealth.smsFailures} failed`}
            label="SMS"
            ok={!deliveryHealth.smsFailures}
            value={deliveryHealth.smsFailures ? "attention" : "healthy"}
          />
          <StatusItem
            detail={
              deliveryHealth.lastSuccessfulDeliveryAt
                ? formatDateTimeWithSeconds(deliveryHealth.lastSuccessfulDeliveryAt)
                : "none yet"
            }
            label="Last success"
            ok={Boolean(deliveryHealth.lastSuccessfulDeliveryAt)}
            value={deliveryHealth.lastSuccessfulDeliveryAt ? "sent" : "pending"}
          />
        </div>
      </section>

      <section className="panel analyticsPanel">
        <div className="panelHeader">
          <h2>Watch Analytics</h2>
          <span>
            {watchAnalytics.totalOpenings} opening
            {watchAnalytics.totalOpenings === 1 ? "" : "s"} found
          </span>
        </div>
        <div className="analyticsGrid">
          <StatusItem
            detail="alerts generated"
            label="Total openings"
            ok={Boolean(watchAnalytics.totalOpenings)}
            value={`${watchAnalytics.totalOpenings}`}
          />
          <StatusItem
            detail={watchAnalytics.topWatch?.parkName ?? "waiting for alerts"}
            label="Hottest watch"
            ok={Boolean(watchAnalytics.topWatch)}
            value={watchAnalytics.topWatch?.label ?? "none yet"}
          />
          <StatusItem
            detail={
              watchAnalytics.latestAlert
                ? formatDateTimeWithSeconds(watchAnalytics.latestAlert.created_at)
                : "none yet"
            }
            label="Latest opening"
            ok={Boolean(watchAnalytics.latestAlert)}
            value={watchAnalytics.latestOpening ?? "pending"}
          />
          <StatusItem
            detail="watches with at least one alert"
            label="Active signal"
            ok={Boolean(watchAnalytics.watchesWithOpenings)}
            value={`${watchAnalytics.watchesWithOpenings} watch${
              watchAnalytics.watchesWithOpenings === 1 ? "" : "es"
            }`}
          />
        </div>
        <div className="hotWatchList">
          {watchAnalytics.hotWatches.length ? (
            watchAnalytics.hotWatches.map((item, index) => (
              <article className="hotWatchItem" key={item.watchId}>
                <span>{index + 1}</span>
                <div>
                  <strong>{item.label}</strong>
                  <p>
                    {item.alertCount} opening{item.alertCount === 1 ? "" : "s"}
                    {item.latestOpening ? ` · latest ${item.latestOpening}` : ""}
                  </p>
                </div>
              </article>
            ))
          ) : (
            <p className="empty compact">
              Watch analytics will populate after the first availability alert.
            </p>
          )}
        </div>
      </section>

      {notice ? <p className="notice">{notice}</p> : null}

      <section className="workspace">
        <form className="panel createPanel" onSubmit={createWatch}>
          <div className="panelHeader">
            <h2>Create Watch</h2>
            <button
              className="iconButton"
              type="submit"
              disabled={busy || selectedCampgroundIds.length === 0}
            >
              <Plus size={18} />
              <span>Add {selectedCampgroundIds.length || ""}</span>
            </button>
          </div>

          <div className="searchRow">
            <label className="autocomplete">
              Park search
              <input
                placeholder="Search a park"
                value={searchQuery}
                onChange={(event) => {
                  setSearchQuery(event.target.value);
                  setShowParkSuggestions(true);
                }}
                onFocus={() => setShowParkSuggestions(parkSuggestions.length > 0)}
              />
              {showParkSuggestions ? (
                <div className="suggestions">
                  {parkSuggestions.map((park) => (
                    <button
                      key={park.recarea_id}
                      type="button"
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => selectParkSuggestion(park)}
                    >
                      <strong>{park.name}</strong>
                      <span>
                        {park.state_code ?? "US"} · {park.campgrounds_count} campground
                        {park.campgrounds_count === 1 ? "" : "s"}
                      </span>
                    </button>
                  ))}
                  {!parkSuggestions.length && !parkLoading ? (
                    <p>No matching parks.</p>
                  ) : null}
                  {parkLoading ? <p>Searching...</p> : null}
                </div>
              ) : null}
            </label>
            <button
              className="iconOnly"
              type="button"
              onClick={() => searchCampgrounds()}
              disabled={busy || searchQuery.trim().length < 2}
              title="Search campgrounds"
            >
              <Search size={18} />
            </button>
          </div>

          <div className="campgroundPicker">
            <div className="pickerHeader">
              <span>Campgrounds</span>
              <div>
                <button
                  type="button"
                  onClick={() =>
                    setSelectedCampgroundIds(
                      campgrounds.map((campground) => campground.facility_id),
                    )
                  }
                >
                  All
                </button>
                <button type="button" onClick={clearCampgroundSearch}>
                  Clear
                </button>
              </div>
            </div>
            <div className="campgroundList">
              {campgrounds.map((campground) => (
                <label className="campgroundOption" key={campground.facility_id}>
                  <input
                    checked={selectedCampgroundIds.includes(campground.facility_id)}
                    type="checkbox"
                    onChange={() => toggleCampground(campground.facility_id)}
                  />
                  <span>
                    <strong>{campground.name}</strong>
                    <em>
                      {campground.city ?? "Unknown city"}
                      {campground.state_code ? `, ${campground.state_code}` : ""} ·{" "}
                      {campground.facility_id}
                    </em>
                  </span>
                </label>
              ))}
              {!campgrounds.length ? (
                <p className="empty compact">Search a park to load campgrounds.</p>
              ) : null}
            </div>
          </div>

          <div className="formGrid">
            <label>
              Start
              <input
                type="date"
                value={dateStart}
                onChange={(event) => setDateStart(event.target.value)}
              />
            </label>
            <label>
              End
              <input
                type="date"
                value={dateEnd}
                onChange={(event) => setDateEnd(event.target.value)}
              />
            </label>
            <label>
              Site type
              <select value={campType} onChange={(event) => setCampType(event.target.value)}>
                <option value="any">Any</option>
                <option value="tent">Tent</option>
                <option value="rv">RV</option>
              </select>
            </label>
            <label>
              Minimum nights
              <input
                type="number"
                min="1"
                max="30"
                value={minNights}
                onChange={(event) =>
                  setMinNights(Math.max(1, Number(event.target.value)))
                }
              />
            </label>
            <label>
              Alerts
              <select
                value={notificationType}
                onChange={(event) => setNotificationType(event.target.value)}
              >
                <option value="both">Email and SMS</option>
                <option value="email">Email</option>
                <option value="sms">SMS</option>
              </select>
            </label>
            <label>
              Email recipient
              <input
                placeholder={settingsStatus?.email.recipient ?? "Use default email"}
                type="email"
                value={alertEmail}
                onChange={(event) => setAlertEmail(event.target.value)}
              />
            </label>
            <label>
              Phone recipient
              <input
                placeholder={settingsStatus?.sms.recipient ?? "Use default phone"}
                type="tel"
                value={alertPhone}
                onChange={(event) => setAlertPhone(event.target.value)}
              />
            </label>
            <label>
              Priority
              <select
                value={watchPriority}
                onChange={(event) =>
                  setWatchPriority(event.target.value as WatchPriority)
                }
              >
                <option value="high">High · 30s</option>
                <option value="normal">Normal · 60s</option>
                <option value="low">Low · 5m</option>
              </select>
            </label>
          </div>
        </form>

        <section className="panel">
          <div className="panelHeader">
            <h2>Watches</h2>
            <span>{watches.length} total</span>
          </div>
          <div className="table">
            {watchGroups.map((group) => (
              <section className="watchGroup" key={group.key}>
                <div className="watchGroupHeader">
                  <div>
                    <strong>{group.parkName}</strong>
                    <p>
                      {group.dateStart} to {group.dateEnd} · {group.minNights}+ night
                      {group.minNights === 1 ? "" : "s"} ·{" "}
                      {formatCampType(group.campType)} ·{" "}
                      {formatNotificationType(group.notificationType)} ·{" "}
                      {formatPriority(group.priority)} priority · every{" "}
                      {formatDuration(group.checkIntervalSeconds)}
                    </p>
                  </div>
                  <div className="groupTools">
                    <div className="groupCounts">
                      <span>
                        {group.watches.length} campground
                        {group.watches.length === 1 ? "" : "s"}
                      </span>
                      <span>
                        {group.nextCheckAt
                          ? `Next availability check ${formatDateTime(
                              group.nextCheckAt,
                            )}`
                          : group.activeCount
                            ? "Availability check pending"
                            : "Paused"}
                      </span>
                      {group.alertCount ? (
                        <span>
                          {group.alertCount} alert
                          {group.alertCount === 1 ? "" : "s"}
                        </span>
                      ) : null}
                      {group.latestAlertAt ? (
                        <span>Latest {formatDateTime(group.latestAlertAt)}</span>
                      ) : null}
                      {group.status === "mixed" && group.activeCount ? (
                        <span>{group.activeCount} active</span>
                      ) : null}
                      {group.status === "mixed" && group.pausedCount ? (
                        <span>{group.pausedCount} paused</span>
                      ) : null}
                      <span className={`status ${group.status}`}>{group.status}</span>
                    </div>
                    <div className="groupActions">
                      {group.activeCount ? (
                        <button
                          className="iconOnly"
                          title="Pause all active watches"
                          onClick={() =>
                            statusGroupAction(
                              group,
                              "paused",
                              "/pause-agent",
                              "Paused",
                            )
                          }
                          disabled={busy}
                        >
                          <Pause size={16} />
                        </button>
                      ) : null}
                      {group.pausedCount ? (
                        <button
                          className="iconOnly"
                          title="Resume all paused watches"
                          onClick={() =>
                            statusGroupAction(
                              group,
                              "active",
                              "/resume-agent",
                              "Resumed",
                            )
                          }
                          disabled={busy}
                        >
                          <Play size={16} />
                        </button>
                      ) : null}
                      <button
                        className="iconOnly"
                        title="Find next available dates for group"
                        onClick={() => findNextAvailableForGroup(group)}
                        disabled={busy || nextLoadingWatch === `group:${group.key}`}
                      >
                        <CalendarDays size={16} />
                      </button>
                      <button
                        className="iconOnly"
                        title="Load strategy recommendations for group"
                        onClick={() => loadRecommendationsForGroup(group)}
                        disabled={
                          busy || recommendationLoadingKey === `group:${group.key}`
                        }
                      >
                        <Compass size={16} />
                      </button>
                      <button
                        className="iconOnly"
                        title="Check group now"
                        onClick={() => checkGroupNow(group)}
                        disabled={busy || group.activeCount === 0}
                      >
                        <RefreshCw size={16} />
                      </button>
                      <button
                        className="iconOnly danger"
                        title="Delete group"
                        onClick={() => beginDeleteGroup(group)}
                        disabled={busy}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                </div>
                <div className="watchGroupList">
                  {group.watches.map((watch) => (
                    <div className="watchItem" key={watch.watch_id}>
                      <div className="row">
                        <div>
                          <strong>{watch.campground_name ?? watch.park_name}</strong>
                          <div className="watchMeta">
                            {watch.facility_id ? (
                              <span>Facility {watch.facility_id}</span>
                            ) : null}
                            <span>
                              {formatPriority(watch.priority)} priority · every{" "}
                              {formatDuration(watch.check_interval_seconds)}
                            </span>
                            {watch.email_address ? (
                              <span>Email {watch.email_address}</span>
                            ) : null}
                            {watch.phone_number_masked ? (
                              <span>SMS {watch.phone_number_masked}</span>
                            ) : null}
                            <span>
                              {watch.last_checked_at
                                ? `Last availability check ${formatDateTime(
                                    watch.last_checked_at,
                                  )}`
                                : "No availability check yet"}
                            </span>
                            {checkLogsByWatchId[watch.watch_id]?.[0] ? (
                              <span>
                                Check{" "}
                                {formatCheckStatus(
                                  checkLogsByWatchId[watch.watch_id][0].status,
                                )}{" "}
                                · {checkLogsByWatchId[watch.watch_id][0].result_count}{" "}
                                result
                                {checkLogsByWatchId[watch.watch_id][0]
                                  .result_count === 1
                                  ? ""
                                  : "s"}
                              </span>
                            ) : null}
                            <span>
                              {nextCheckByWatchId[watch.watch_id]
                                ? `Next availability check ${formatDateTime(
                                    nextCheckByWatchId[watch.watch_id],
                                  )}`
                                : watch.status === "paused"
                                  ? "Paused"
                                  : "Availability check pending"}
                            </span>
                          </div>
                        </div>
                        <span className={`status ${watch.status}`}>
                          {watch.status}
                        </span>
                        <div className="actions">
                          {watch.status === "active" ? (
                            <button
                              className="iconOnly"
                              title="Pause"
                              onClick={() =>
                                statusAction("/pause-agent", watch.watch_id)
                              }
                            >
                              <Pause size={17} />
                            </button>
                          ) : (
                            <button
                              className="iconOnly"
                              title="Resume"
                              onClick={() =>
                                statusAction("/resume-agent", watch.watch_id)
                              }
                            >
                              <Play size={17} />
                            </button>
                          )}
                          <button
                            className="iconOnly"
                            title="Edit"
                            onClick={() => beginEdit(watch)}
                          >
                            <Pencil size={17} />
                          </button>
                          <button
                            className="iconOnly"
                            title="Find next available dates"
                            onClick={() => findNextAvailable(watch.watch_id)}
                            disabled={nextLoadingWatch === watch.watch_id}
                          >
                            <CalendarDays size={17} />
                          </button>
                          <button
                            className="iconOnly"
                            title="Load strategy recommendations"
                            onClick={() => loadRecommendationsForWatch(watch.watch_id)}
                            disabled={recommendationLoadingKey === watch.watch_id}
                          >
                            <Compass size={17} />
                          </button>
                          <button
                            className="iconOnly"
                            title="Check now"
                            onClick={() =>
                              postAction(`/watches/${watch.watch_id}/check-now`)
                            }
                          >
                            <RefreshCw size={17} />
                          </button>
                          <button
                            className="iconOnly danger"
                            title="Delete"
                            onClick={() => beginDeleteWatch(watch)}
                          >
                            <Trash2 size={17} />
                          </button>
                        </div>
                      </div>
                      {editingWatchId === watch.watch_id && editDraft ? (
                        <div className="editWatch">
                          <label>
                            Start
                            <input
                              type="date"
                              value={editDraft.date_start}
                              onChange={(event) =>
                                setEditDraft({
                                  ...editDraft,
                                  date_start: event.target.value,
                                })
                              }
                            />
                          </label>
                          <label>
                            End
                            <input
                              type="date"
                              value={editDraft.date_end}
                              onChange={(event) =>
                                setEditDraft({
                                  ...editDraft,
                                  date_end: event.target.value,
                                })
                              }
                            />
                          </label>
                          <label>
                            Site type
                            <select
                              value={editDraft.camp_type}
                              onChange={(event) =>
                                setEditDraft({
                                  ...editDraft,
                                  camp_type: event.target.value,
                                })
                              }
                            >
                              <option value="any">Any</option>
                              <option value="tent">Tent</option>
                              <option value="rv">RV</option>
                            </select>
                          </label>
                          <label>
                            Min nights
                            <input
                              type="number"
                              min="1"
                              max="30"
                              value={editDraft.min_nights}
                              onChange={(event) =>
                                setEditDraft({
                                  ...editDraft,
                                  min_nights: Math.max(1, Number(event.target.value)),
                                })
                              }
                            />
                          </label>
                          <label>
                            Alerts
                            <select
                              value={editDraft.notification_type}
                              onChange={(event) =>
                                setEditDraft({
                                  ...editDraft,
                                  notification_type: event.target
                                    .value as Watch["notification_type"],
                                })
                              }
                            >
                              <option value="both">Email and SMS</option>
                              <option value="email">Email</option>
                              <option value="sms">SMS</option>
                            </select>
                          </label>
                          <label>
                            Email recipient
                            <input
                              placeholder={
                                settingsStatus?.email.recipient ?? "Use default email"
                              }
                              type="email"
                              value={editDraft.email_address}
                              onChange={(event) =>
                                setEditDraft({
                                  ...editDraft,
                                  email_address: event.target.value,
                                })
                              }
                            />
                          </label>
                          <label>
                            Phone recipient
                            <input
                              placeholder={
                                watch.phone_number_masked
                                  ? `${watch.phone_number_masked} · type to replace`
                                  : settingsStatus?.sms.recipient ?? "Use default phone"
                              }
                              type="tel"
                              value={editDraft.phone_number}
                              onChange={(event) =>
                                setEditDraft({
                                  ...editDraft,
                                  phone_number: event.target.value,
                                })
                              }
                            />
                          </label>
                          <label>
                            Priority
                            <select
                              value={editDraft.priority}
                              onChange={(event) =>
                                setEditDraft({
                                  ...editDraft,
                                  priority: event.target.value as WatchPriority,
                                })
                              }
                            >
                              <option value="high">High · 30s</option>
                              <option value="normal">Normal · 60s</option>
                              <option value="low">Low · 5m</option>
                            </select>
                          </label>
                          <div className="editActions">
                            <button
                              className="iconOnly"
                              title="Save"
                              onClick={() => saveWatchEdit(watch.watch_id)}
                              disabled={busy}
                            >
                              <Save size={17} />
                            </button>
                            <button
                              className="iconOnly"
                              title="Cancel"
                              onClick={cancelEdit}
                            >
                              <X size={17} />
                            </button>
                          </div>
                        </div>
                      ) : null}
                      {nextOpenings[watch.watch_id] ? (
                        <div className="nextOpenings">
                          {nextOpenings[watch.watch_id].length ? (
                            nextOpenings[watch.watch_id].map((opening) => (
                              <a
                                className="opening"
                                href={opening.reservation_url}
                                key={`${opening.available_date}-${opening.available_end_date}-${opening.nights}`}
                                rel="noreferrer"
                                target="_blank"
                              >
                                <strong>
                                  {opening.available_date} to{" "}
                                  {opening.available_end_date}
                                </strong>
                                <span>
                                  {opening.nights} night
                                  {opening.nights === 1 ? "" : "s"} ·{" "}
                                  {opening.site_count} site
                                  {opening.site_count === 1 ? "" : "s"}
                                </span>
                              </a>
                            ))
                          ) : (
                            <p className="empty compact">
                              No openings found in 90 days.
                            </p>
                          )}
                        </div>
                      ) : null}
                      {recommendations[watch.watch_id] ? (
                        <div className="recommendations">
                          <div className="recommendationHeader">
                            <span>Strategy recommendations</span>
                            <span>{recommendations[watch.watch_id].length} found</span>
                          </div>
                          {recommendations[watch.watch_id].length ? (
                            recommendations[watch.watch_id].map((recommendation) => (
                              <a
                                className="recommendation"
                                href={recommendation.reservation_url}
                                key={recommendation.recommendation_id}
                                rel="noreferrer"
                                target="_blank"
                              >
                                <div>
                                  <strong>{recommendation.campground_name}</strong>
                                  <p>{recommendation.reason}</p>
                                </div>
                                <div className="recommendationMeta">
                                  <span>
                                    {formatRecommendationType(
                                      recommendation.match_type,
                                    )}
                                  </span>
                                  <span>
                                    {recommendation.available_date} to{" "}
                                    {recommendation.available_end_date}
                                  </span>
                                  <span>
                                    {recommendation.nights} night
                                    {recommendation.nights === 1 ? "" : "s"}
                                  </span>
                                  <span>
                                    {recommendation.site_count} site
                                    {recommendation.site_count === 1 ? "" : "s"}
                                  </span>
                                  <span>score {recommendation.score}</span>
                                </div>
                              </a>
                            ))
                          ) : (
                            <p className="empty compact">
                              No strategy recommendations found.
                            </p>
                          )}
                        </div>
                      ) : null}
                      <WatchAlertHistory alerts={alertsByWatchId[watch.watch_id] ?? []} />
                    </div>
                  ))}
                </div>
              </section>
            ))}
            {!watchGroups.length ? <p className="empty">No watches yet.</p> : null}
          </div>
        </section>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Alerts</h2>
          <div className="panelControls">
            <select
              value={alertWatchFilter}
              onChange={(event) => setAlertWatchFilter(event.target.value)}
            >
              <option value="all">All watches</option>
              {watches.map((watch) => (
                <option key={watch.watch_id} value={watch.watch_id}>
                  {watch.campground_name ?? watch.park_name}
                </option>
              ))}
            </select>
            <select
              value={alertDeliveryFilter}
              onChange={(event) =>
                setAlertDeliveryFilter(event.target.value as AlertDeliveryFilter)
              }
            >
              <option value="all">All deliveries</option>
              <option value="sent">Sent only</option>
              <option value="needs_retry">Needs retry</option>
              <option value="email_failed">Email failed</option>
              <option value="sms_failed">SMS failed</option>
            </select>
            <span>{filteredAlerts.length} shown</span>
          </div>
        </div>
        <div className="alertList">
          {filteredAlerts.map((alert) => {
            const bookingIntent = bookingIntentByAlertId[alert.alert_id];
            return (
              <article className="alertItem" key={alert.alert_id}>
                <div>
                  <strong>
                    {alert.campground_name ?? alert.park_name}
                    {alert.site ? ` · site ${alert.site}` : ""}
                  </strong>
                  <p>{alert.message}</p>
                  <div className="alertMeta">
                    <span>{new Date(alert.created_at).toLocaleString()}</span>
                    {alert.available_date && alert.available_end_date ? (
                      <span>
                        {alert.available_date} to {alert.available_end_date}
                      </span>
                    ) : null}
                    {alert.nights ? (
                      <span>
                        {alert.nights} night{alert.nights === 1 ? "" : "s"}
                      </span>
                    ) : null}
                    {alert.site_type ? <span>{alert.site_type}</span> : null}
                    {bookingIntent ? (
                      <span className={`bookingStatus ${bookingIntent.status}`}>
                        Book Assist: {formatBookingStatus(bookingIntent.status)}
                      </span>
                    ) : null}
                  </div>
                  <div className="deliveries">
                    {alert.deliveries.length ? (
                      alert.deliveries.map((delivery) => (
                        <span
                          className={`delivery ${delivery.status}`}
                          key={`${alert.alert_id}-${delivery.channel}`}
                          title={delivery.detail}
                        >
                          {delivery.channel}: {delivery.status}
                        </span>
                      ))
                    ) : (
                      <span className="delivery not_configured">
                        no delivery record
                      </span>
                    )}
                  </div>
                  {bookingIntent ? (
                    <div className="bookingIntent">
                      <p>{bookingIntent.note}</p>
                      <div className="bookingIntentMeta">
                        <span>Created {formatDateTimeWithSeconds(bookingIntent.created_at)}</span>
                        <span>Updated {formatDateTimeWithSeconds(bookingIntent.updated_at)}</span>
                        {bookingIntent.site ? <span>Site {bookingIntent.site}</span> : null}
                      </div>
                    </div>
                  ) : null}
                </div>
                <div className="alertActions">
                  <button
                    className="iconButton"
                    disabled={busy || bookingIntentBusyAlertId === alert.alert_id}
                    onClick={() => startBookAssist(alert)}
                    title="Create a booking handoff and open Recreation.gov"
                    type="button"
                  >
                    <ExternalLink size={16} />
                    <span>
                      {bookingIntentBusyAlertId === alert.alert_id
                        ? "Opening"
                        : "Book Assist"}
                    </span>
                  </button>
                  {bookingIntent ? (
                    <a
                      href={bookingIntent.handoff_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Handoff
                    </a>
                  ) : null}
                  {bookingIntent &&
                  bookingIntent.status !== "user_confirmed" ? (
                    <button
                      className="iconButton"
                      disabled={busy || bookingStatusBusyId === bookingIntent.booking_intent_id}
                      onClick={() =>
                        updateBookingIntentStatus(
                          bookingIntent.booking_intent_id,
                          "user-confirmed",
                        )
                      }
                      title="Mark this handoff as booked by the user"
                      type="button"
                    >
                      <CheckCircle2 size={16} />
                      <span>Booked</span>
                    </button>
                  ) : null}
                  {bookingIntent &&
                  bookingIntent.status !== "abandoned" &&
                  bookingIntent.status !== "user_confirmed" ? (
                    <button
                      className="iconButton"
                      disabled={busy || bookingStatusBusyId === bookingIntent.booking_intent_id}
                      onClick={() =>
                        updateBookingIntentStatus(
                          bookingIntent.booking_intent_id,
                          "abandoned",
                        )
                      }
                      title="Mark this handoff as abandoned"
                      type="button"
                    >
                      <X size={16} />
                      <span>Abandon</span>
                    </button>
                  ) : null}
                  {hasRetryableDelivery(alert) ? (
                    <button
                      className="iconButton"
                      disabled={busy || retryingAlertId === alert.alert_id}
                      onClick={() => retryAlertDelivery(alert.alert_id)}
                      title="Retry failed delivery"
                      type="button"
                    >
                      <RefreshCw size={16} />
                      <span>
                        {retryingAlertId === alert.alert_id ? "Retrying" : "Retry"}
                      </span>
                    </button>
                  ) : null}
                  <a href={alert.reservation_url} target="_blank" rel="noreferrer">
                    Open
                  </a>
                </div>
              </article>
            );
          })}
          {!filteredAlerts.length ? (
            <p className="empty">No alerts for the selected watches.</p>
          ) : null}
        </div>
      </section>
      <section className="panel">
        <div className="panelHeader">
          <h2>Check History</h2>
          <span>
            {checkLogs.length} recent check{checkLogs.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="checkLogList">
          {checkLogs.slice(0, 25).map((log) => (
            <article className="checkLogItem" key={log.log_id}>
              <div>
                <strong>{watchLabelById[log.watch_id] ?? log.watch_id}</strong>
                <p>
                  {log.top_match_summary ??
                    log.error_message ??
                    "No matching availability found."}
                </p>
              </div>
              <div className="checkLogMeta">
                <span className={`delivery ${log.status === "success" ? "sent" : "failed"}`}>
                  {formatCheckStatus(log.status)}
                </span>
                <span>{formatDateTimeWithSeconds(log.checked_at)}</span>
                <span>
                  {log.result_count} result{log.result_count === 1 ? "" : "s"}
                </span>
                {log.alert_created ? <span>alert sent</span> : null}
              </div>
            </article>
          ))}
          {!checkLogs.length ? (
            <p className="empty">
              Check history will appear after the scheduler or Check now runs.
            </p>
          ) : null}
        </div>
      </section>
      {deleteTarget ? (
        <div
          aria-labelledby="delete-watch-title"
          aria-modal="true"
          className="modalBackdrop"
          role="dialog"
        >
          <div className="confirmDialog">
            <div>
              <p className="eyebrow">
                Delete {deleteTarget.type === "watch" ? "Watch" : "Group"}
              </p>
              <h2 id="delete-watch-title">
                {deleteTarget.type === "watch"
                  ? `Delete ${
                      deleteTarget.watch.campground_name ??
                      deleteTarget.watch.park_name
                    }?`
                  : `Delete ${deleteTarget.group.parkName} group?`}
              </h2>
            </div>
            <div className="confirmMeta">
              <span>
                {deleteTarget.type === "watch"
                  ? deleteTarget.watch.park_name
                  : `${deleteTarget.group.watches.length} campground${
                      deleteTarget.group.watches.length === 1 ? "" : "s"
                    }`}
              </span>
              <span>
                {deleteTarget.type === "watch"
                  ? `${deleteTarget.watch.date_start} to ${deleteTarget.watch.date_end}`
                  : `${deleteTarget.group.dateStart} to ${deleteTarget.group.dateEnd}`}
              </span>
              <span>
                {deleteTarget.type === "watch"
                  ? deleteTarget.watch.min_nights
                  : deleteTarget.group.minNights}
                + night
                {(deleteTarget.type === "watch"
                  ? deleteTarget.watch.min_nights
                  : deleteTarget.group.minNights) === 1
                  ? ""
                  : "s"}
              </span>
              <span>
                {formatNotificationType(
                  deleteTarget.type === "watch"
                    ? deleteTarget.watch.notification_type
                    : deleteTarget.group.notificationType,
                )}
              </span>
              <span>
                {formatPriority(
                  deleteTarget.type === "watch"
                    ? deleteTarget.watch.priority
                    : deleteTarget.group.priority,
                )}{" "}
                priority
              </span>
            </div>
            {deleteTarget.type === "group" ? (
              <div className="confirmList">
                {deleteTarget.group.watches.map((watch) => (
                  <span key={watch.watch_id}>
                    {watch.campground_name ?? watch.park_name}
                  </span>
                ))}
              </div>
            ) : null}
            <p className="confirmText">
              {deleteTarget.type === "watch"
                ? "This will remove the watch and its alert history."
                : "This will remove every watch in this group and their alert histories."}
            </p>
            <div className="modalActions">
              <button
                className="iconButton"
                disabled={busy}
                onClick={cancelDelete}
                type="button"
              >
                <X size={17} />
                <span>Cancel</span>
              </button>
              <button
                className="iconButton dangerButton"
                disabled={busy}
                onClick={confirmDelete}
                type="button"
              >
                <Trash2 size={17} />
                <span>
                  {deleteTarget.type === "watch" ? "Delete" : "Delete Group"}
                </span>
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}

function parseApiError(message: string) {
  if (!message) {
    return "";
  }

  try {
    const parsed = JSON.parse(message) as {
      detail?: string | { msg?: string }[];
    };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail)) {
      return parsed.detail
        .map((item) => item.msg)
        .filter(Boolean)
        .join(" ");
    }
  } catch {
    return message;
  }

  return message;
}

function formatTestDelivery(delivery: {
  channel: string;
  status: string;
  detail: string;
}) {
  if (delivery.status === "sent") {
    return `${delivery.channel} sent`;
  }

  const detail = delivery.detail ? `: ${compactDetail(delivery.detail)}` : "";
  return `${delivery.channel} ${delivery.status}${detail}`;
}

function compactDetail(detail: string) {
  return detail.replace(/\s+/g, " ").slice(0, 220);
}

function isFailedDelivery(delivery: Alert["deliveries"][number]) {
  return delivery.status === "failed" || delivery.status === "not_configured";
}

function hasRetryableDelivery(alert: Alert) {
  if (!alert.deliveries.length) {
    return true;
  }

  return alert.deliveries.some(isFailedDelivery);
}

function upsertBookingIntent(
  current: BookingIntent[],
  bookingIntent: BookingIntent,
) {
  const withoutIntent = current.filter(
    (intent) => intent.booking_intent_id !== bookingIntent.booking_intent_id,
  );
  return [bookingIntent, ...withoutIntent];
}

function formatBookingStatus(status: BookingIntentStatus) {
  if (status === "user_confirmed") {
    return "user confirmed";
  }
  return status;
}

function alertMatchesDeliveryFilter(
  alert: Alert,
  deliveryFilter: AlertDeliveryFilter,
) {
  if (deliveryFilter === "all") {
    return true;
  }

  if (deliveryFilter === "needs_retry") {
    return hasRetryableDelivery(alert);
  }

  if (deliveryFilter === "sent") {
    return (
      alert.deliveries.length > 0 &&
      alert.deliveries.every((delivery) => delivery.status === "sent")
    );
  }

  const failedChannel = deliveryFilter === "email_failed" ? "email" : "sms";
  return alert.deliveries.some(
    (delivery) => delivery.channel === failedChannel && isFailedDelivery(delivery),
  );
}

function formatCampType(campType: string) {
  if (campType === "any") {
    return "any site";
  }
  if (campType === "rv") {
    return "RV";
  }
  return campType;
}

function formatNotificationType(notificationType: Watch["notification_type"]) {
  if (notificationType === "both") {
    return "email and SMS";
  }
  return notificationType;
}

function formatPriority(priority: WatchPriority) {
  if (priority === "high") {
    return "High";
  }
  if (priority === "low") {
    return "Low";
  }
  return "Normal";
}

function formatDuration(seconds: number) {
  if (seconds >= 120 && seconds % 60 === 0) {
    const minutes = seconds / 60;
    return `${minutes}m`;
  }
  return `${seconds}s`;
}

function prioritySortRank(priority: WatchPriority) {
  if (priority === "high") {
    return 0;
  }
  if (priority === "normal") {
    return 1;
  }
  return 2;
}

function formatRecommendationType(
  matchType: StrategyRecommendation["match_type"],
) {
  if (matchType === "exact_match") {
    return "exact match";
  }
  if (matchType === "same_park") {
    return "same park";
  }
  return "flexible date";
}

function formatCheckStatus(status: ReservationCheckLog["status"]) {
  if (status === "success") {
    return "success";
  }
  return "failed";
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "";
  }

  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDateTimeWithSeconds(value: string | null | undefined) {
  if (!value) {
    return "";
  }

  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="metric">
      <div className="metricIcon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}

function StatusItem({
  detail,
  label,
  ok,
  value,
}: {
  detail?: string | null;
  label: string;
  ok?: boolean;
  value: string;
}) {
  return (
    <div className="statusItem">
      <span className={`statusDot ${ok ? "ok" : "warn"}`} />
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        {detail ? <p>{detail}</p> : null}
      </div>
    </div>
  );
}

function WatchAlertHistory({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length) {
    return null;
  }

  const visibleAlerts = alerts.slice(0, 3);
  const hiddenCount = alerts.length - visibleAlerts.length;

  return (
    <div className="watchAlerts">
      <div className="watchAlertsHeader">
        <span>Alert history</span>
        <span>
          {alerts.length} total alert{alerts.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="watchAlertList">
        {visibleAlerts.map((alert) => (
          <a
            className="watchAlert"
            href={alert.reservation_url}
            key={alert.alert_id}
            rel="noreferrer"
            target="_blank"
          >
            <strong>
              {alert.available_date && alert.available_end_date
                ? `${alert.available_date} to ${alert.available_end_date}`
                : formatDateTime(alert.created_at)}
              {alert.site ? ` · site ${alert.site}` : ""}
            </strong>
            <p>{alert.message}</p>
            <div className="alertMeta">
              <span>{formatDateTime(alert.created_at)}</span>
              {alert.nights ? (
                <span>
                  {alert.nights} night{alert.nights === 1 ? "" : "s"}
                </span>
              ) : null}
              {alert.site_type ? <span>{alert.site_type}</span> : null}
            </div>
            <div className="deliveries">
              {alert.deliveries.length ? (
                alert.deliveries.map((delivery) => (
                  <span
                    className={`delivery ${delivery.status}`}
                    key={`${alert.alert_id}-${delivery.channel}`}
                    title={delivery.detail}
                  >
                    {delivery.channel}: {delivery.status}
                  </span>
                ))
              ) : (
                <span className="delivery not_configured">no delivery record</span>
              )}
            </div>
          </a>
        ))}
      </div>
      {hiddenCount ? (
        <p className="watchAlertsMore">
          {hiddenCount} more alert{hiddenCount === 1 ? "" : "s"} in the full log
        </p>
      ) : null}
    </div>
  );
}
