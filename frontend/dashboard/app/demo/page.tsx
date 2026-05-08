import {
  Activity,
  Bell,
  CalendarDays,
  CheckCircle2,
  Compass,
  Database,
  ExternalLink,
  Lock,
  Pause,
  Pencil,
  Play,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  TrendingUp,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

const demoWatches = [
  {
    alerts: 3,
    campground: "Upper Pines",
    checkInterval: "30s",
    facilityId: "232447",
    lastChecked: "May 6, 2:14:22 PM",
    nextCheck: "May 6, 2:14:52 PM",
    priority: "High",
    status: "active",
  },
  {
    alerts: 1,
    campground: "Lower Pines",
    checkInterval: "30s",
    facilityId: "232450",
    lastChecked: "May 6, 2:14:18 PM",
    nextCheck: "May 6, 2:14:48 PM",
    priority: "High",
    status: "active",
  },
  {
    alerts: 0,
    campground: "North Pines",
    checkInterval: "60s",
    facilityId: "232449",
    lastChecked: "May 6, 2:13:57 PM",
    nextCheck: "May 6, 2:14:57 PM",
    priority: "Normal",
    status: "paused",
  },
];

const demoOpenings = [
  {
    alertCount: 3,
    campground: "Upper Pines",
    latestOpening: "2026-06-11 to 2026-06-12",
  },
  {
    alertCount: 1,
    campground: "Lower Pines",
    latestOpening: "2026-06-10 to 2026-06-12",
  },
];

const demoAlerts = [
  {
    campground: "Upper Pines",
    createdAt: "May 6, 2:14:22 PM",
    deliveries: ["email: sent", "sms: sent"],
    message:
      "Matching opening found for 1 night inside the selected Yosemite date window.",
    bookAssistStatus: "opened",
    site: "Site 042",
    window: "2026-06-11 to 2026-06-12",
  },
  {
    campground: "Lower Pines",
    createdAt: "May 6, 2:12:09 PM",
    deliveries: ["email: sent", "sms: sent"],
    message:
      "Two-night opening found for a tent-friendly site in the monitored range.",
    bookAssistStatus: "user confirmed",
    site: "Site 018",
    window: "2026-06-10 to 2026-06-12",
  },
];

const demoRecommendations = [
  {
    campground: "Upper Pines",
    reason: "Matches the selected watch window and filters.",
    score: 104,
    type: "exact match",
    window: "2026-06-11 to 2026-06-12",
  },
  {
    campground: "Wawona",
    reason: "Same-park campground alternative inside the selected window.",
    score: 80,
    type: "same park",
    window: "2026-06-10 to 2026-06-12",
  },
  {
    campground: "Upper Pines",
    reason: "Same campground outside the selected window within 90 days.",
    score: 59,
    type: "flexible date",
    window: "2026-06-17 to 2026-06-18",
  },
];

const demoCheckLogs = [
  {
    checkedAt: "May 6, 2:14:22 PM",
    campground: "Upper Pines",
    resultCount: 3,
    status: "success",
    summary: "Upper Pines site 042 for 1 night from 2026-06-11 to 2026-06-12.",
  },
  {
    checkedAt: "May 6, 2:14:18 PM",
    campground: "Lower Pines",
    resultCount: 1,
    status: "success",
    summary: "Lower Pines site 018 for 2 nights from 2026-06-10 to 2026-06-12.",
  },
  {
    checkedAt: "May 6, 2:13:57 PM",
    campground: "North Pines",
    resultCount: 0,
    status: "success",
    summary: "No matching availability found.",
  },
];

export default function DemoDashboard() {
  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">ParkReserve AI Demo</p>
          <h1>Reservation Monitor</h1>
        </div>
        <div className="topbarActions">
          <div className="refreshMeta">
            <span>Dashboard updated May 6, 2:14:22 PM</span>
            <span>Dashboard refresh in 30s</span>
          </div>
          <Link className="iconButton" href="/">
            <Lock size={18} />
            <span>Private Dashboard</span>
          </Link>
        </div>
      </header>

      <p className="demoBanner">Demo mode: sample data only. Actions are disabled.</p>

      <section className="metrics">
        <Metric icon={<CalendarDays size={18} />} label="Active Watches" value={2} />
        <Metric icon={<Bell size={18} />} label="Alerts" value={4} />
        <Metric icon={<Activity size={18} />} label="Checks" value={3} />
        <Metric icon={<TrendingUp size={18} />} label="Hot Watches" value={2} />
        <Metric icon={<ShieldCheck size={18} />} label="Delivery Health" value="100%" />
        <Metric icon={<Play size={18} />} label="Scheduled Jobs" value={2} />
        <Metric icon={<Database size={18} />} label="Store" value="Demo" />
      </section>

      <section className="panel statusPanel">
        <div className="panelHeader">
          <h2>System Status</h2>
          <div className="panelHeaderActions">
            <span>demo</span>
            <button className="iconButton" disabled type="button">
              <Send size={17} />
              <span>Test Email</span>
            </button>
            <button className="iconButton" disabled type="button">
              <Send size={17} />
              <span>Test SMS</span>
            </button>
          </div>
        </div>
        <div className="statusGrid">
          <StatusItem detail="demo@example.com" label="Email" ok value="configured" />
          <StatusItem detail="***-***-5120" label="SMS" ok value="configured" />
          <StatusItem detail="60s" label="Base check" ok value="normal priority" />
          <StatusItem detail="3 recent checks" label="Check logs" ok value="healthy" />
          <StatusItem detail="30s" label="Refresh" ok value="dashboard" />
          <StatusItem detail="private backend locked" label="API auth" ok value="protected" />
          <StatusItem detail="public search" label="RIDB" ok value="optional" />
        </div>
      </section>

      <section className="panel deliveryPanel">
        <div className="panelHeader">
          <h2>Delivery Health</h2>
          <span>8/8 sent</span>
        </div>
        <div className="healthGrid">
          <StatusItem detail="8 sent of 8" label="Success rate" ok value="100%" />
          <StatusItem detail="failed or missing channels" label="Needs retry" ok value="0 alerts" />
          <StatusItem detail="0 failed" label="Email" ok value="healthy" />
          <StatusItem detail="0 failed" label="SMS" ok value="healthy" />
          <StatusItem detail="May 6, 2:14:22 PM" label="Last success" ok value="sent" />
        </div>
      </section>

      <section className="panel analyticsPanel">
        <div className="panelHeader">
          <h2>Watch Analytics</h2>
          <span>4 openings found</span>
        </div>
        <div className="analyticsGrid">
          <StatusItem detail="alerts generated" label="Total openings" ok value="4" />
          <StatusItem detail="Yosemite National Park" label="Hottest watch" ok value="Upper Pines" />
          <StatusItem detail="May 6, 2:14:22 PM" label="Latest opening" ok value="2026-06-11 to 2026-06-12" />
          <StatusItem detail="watches with at least one alert" label="Active signal" ok value="2 watches" />
        </div>
        <div className="hotWatchList">
          {demoOpenings.map((opening, index) => (
            <article className="hotWatchItem" key={opening.campground}>
              <span>{index + 1}</span>
              <div>
                <strong>{opening.campground}</strong>
                <p>
                  {opening.alertCount} opening{opening.alertCount === 1 ? "" : "s"} - latest{" "}
                  {opening.latestOpening}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="demoWorkspace">
        <section className="panel createPanel">
          <div className="panelHeader">
            <h2>Create Watch</h2>
            <button className="iconButton" disabled type="button">
              <Search size={18} />
              <span>Demo Only</span>
            </button>
          </div>
          <div className="demoControlGrid">
            <PreviewField label="Park search" value="Yosemite National Park" />
            <PreviewField label="Campgrounds" value="Upper Pines, Lower Pines, North Pines" />
            <PreviewField label="Start" value="06/10/2026" />
            <PreviewField label="End" value="06/13/2026" />
            <PreviewField label="Site type" value="Any" />
            <PreviewField label="Minimum nights" value="1" />
            <PreviewField label="Alerts" value="Email and SMS" />
            <PreviewField label="Priority" value="High" />
          </div>
        </section>

        <section className="panel">
          <div className="panelHeader">
            <h2>Watches</h2>
            <span>{demoWatches.length} total</span>
          </div>
          <div className="table">
            <section className="watchGroup">
              <div className="watchGroupHeader">
                <div>
                  <strong>Yosemite National Park</strong>
                  <p>
                    2026-06-10 to 2026-06-13 - 1+ night - any site - email and SMS - high priority
                  </p>
                </div>
                <div className="groupTools">
                  <div className="groupCounts">
                    <span>3 campgrounds</span>
                    <span>Next availability check May 6, 2:14 PM</span>
                    <span>4 alerts</span>
                    <span className="status mixed">mixed</span>
                  </div>
                  <DisabledActions />
                </div>
              </div>
              <div className="watchGroupList">
                {demoWatches.map((watch) => (
                  <article className="watchItem" key={watch.facilityId}>
                    <div className="row">
                      <div>
                        <strong>{watch.campground}</strong>
                        <div className="watchMeta">
                          <span>Facility {watch.facilityId}</span>
                          <span>
                            {watch.priority} priority - every {watch.checkInterval}
                          </span>
                          <span>Last availability check {watch.lastChecked}</span>
                          <span>Next availability check {watch.nextCheck}</span>
                          {watch.alerts ? (
                            <span>
                              {watch.alerts} alert{watch.alerts === 1 ? "" : "s"}
                            </span>
                          ) : null}
                        </div>
                      </div>
                      <span className={`status ${watch.status}`}>{watch.status}</span>
                      <DisabledActions compact />
                    </div>
                  </article>
                ))}
              </div>
              <div className="recommendations">
                <div className="recommendationHeader">
                  <span>Strategy recommendations</span>
                  <span>{demoRecommendations.length} found</span>
                </div>
                {demoRecommendations.map((recommendation) => (
                  <div className="recommendation" key={`${recommendation.type}-${recommendation.window}`}>
                    <div>
                      <strong>{recommendation.campground}</strong>
                      <p>{recommendation.reason}</p>
                    </div>
                    <div className="recommendationMeta">
                      <span>{recommendation.type}</span>
                      <span>{recommendation.window}</span>
                      <span>1+ night</span>
                      <span>score {recommendation.score}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </section>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <h2>Alerts</h2>
          <div className="panelControls">
            <select disabled value="all">
              <option value="all">All deliveries</option>
            </select>
            <span>{demoAlerts.length} shown</span>
          </div>
        </div>
        <div className="alertList">
          {demoAlerts.map((alert) => (
            <article className="alertItem" key={`${alert.campground}-${alert.site}`}>
              <div>
                <strong>
                  {alert.campground} - {alert.site}
                </strong>
                <p>{alert.message}</p>
                <div className="alertMeta">
                  <span>{alert.createdAt}</span>
                  <span>{alert.window}</span>
                  <span>1+ night</span>
                  <span>standard nonelectric</span>
                  <span className="bookingStatus opened">
                    Book Assist: {alert.bookAssistStatus}
                  </span>
                </div>
                <div className="deliveries">
                  {alert.deliveries.map((delivery) => (
                    <span className="delivery sent" key={delivery}>
                      {delivery}
                    </span>
                  ))}
                </div>
                <div className="bookingIntent">
                  <p>
                    Book Assist opens Recreation.gov with the matching campground
                    and dates. The user completes checkout manually.
                  </p>
                  <div className="bookingIntentMeta">
                    <span>Created May 6, 2:14:22 PM</span>
                    <span>Updated May 6, 2:14:35 PM</span>
                    <span>{alert.site}</span>
                  </div>
                </div>
              </div>
              <div className="alertActions">
                <button className="iconButton" disabled type="button">
                  <ExternalLink size={16} />
                  <span>Book Assist</span>
                </button>
                <button className="iconButton" disabled type="button">
                  <CheckCircle2 size={16} />
                  <span>Booked</span>
                </button>
                <button className="iconButton" disabled type="button">
                  <X size={16} />
                  <span>Abandon</span>
                </button>
                <button className="iconButton" disabled type="button">
                  <RefreshCw size={16} />
                  <span>Retry</span>
                </button>
                <span className="demoLocked">Demo only</span>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section className="panel">
        <div className="panelHeader">
          <h2>Check History</h2>
          <span>{demoCheckLogs.length} recent checks</span>
        </div>
        <div className="checkLogList">
          {demoCheckLogs.map((log) => (
            <article className="checkLogItem" key={`${log.campground}-${log.checkedAt}`}>
              <div>
                <strong>{log.campground}</strong>
                <p>{log.summary}</p>
              </div>
              <div className="checkLogMeta">
                <span className="delivery sent">{log.status}</span>
                <span>{log.checkedAt}</span>
                <span>
                  {log.resultCount} result{log.resultCount === 1 ? "" : "s"}
                </span>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function DisabledActions({ compact = false }: { compact?: boolean }) {
  return (
    <div className={compact ? "actions" : "groupActions"}>
      <button className="iconOnly" disabled title="Pause" type="button">
        <Pause size={compact ? 17 : 16} />
      </button>
      <button className="iconOnly" disabled title="Resume" type="button">
        <Play size={compact ? 17 : 16} />
      </button>
      <button className="iconOnly" disabled title="Edit" type="button">
        <Pencil size={compact ? 17 : 16} />
      </button>
      <button className="iconOnly" disabled title="Find next available dates" type="button">
        <CalendarDays size={compact ? 17 : 16} />
      </button>
      <button className="iconOnly" disabled title="Load strategy recommendations" type="button">
        <Compass size={compact ? 17 : 16} />
      </button>
      <button className="iconOnly" disabled title="Check now" type="button">
        <RefreshCw size={compact ? 17 : 16} />
      </button>
      <button className="iconOnly danger" disabled title="Delete" type="button">
        <Trash2 size={compact ? 17 : 16} />
      </button>
    </div>
  );
}

function PreviewField({ label, value }: { label: string; value: string }) {
  return (
    <div className="demoField">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
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
