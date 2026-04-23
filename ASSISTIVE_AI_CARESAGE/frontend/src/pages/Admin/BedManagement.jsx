import { useState, useEffect, useCallback } from "react";
import { 
    LayoutDashboard, 
    Bed as BedIcon, 
    User, 
    Clock, 
    Activity, 
    Truck, 
    AlertCircle, 
    CheckCircle,
    XCircle,
    RefreshCw,
    LogOut,
    ChevronRight,
    MapPin,
    ClipboardList,
} from "lucide-react";
import { BedAPI, EncounterAPI } from "../../api/client";
import HandoffModal from "../../components/HandoffModal"; 

export default function BedManagement() {
    const [status, setStatus] = useState(null);
    const [stats, setStats] = useState(null);
    const [beds, setBeds] = useState([]);
    const [queue, setQueue] = useState([]);
    const [ambulances, setAmbulances] = useState([]);
    const [loading, setLoading] = useState(true);
    const [alerts, setAlerts] = useState([]);
    const [handoffEnc, setHandoffEnc] = useState(null);

    const fetchData = useCallback(async () => {
        try {
            const data = await EncounterAPI.getDashboardStatus();
            setStatus(data);
            
            // Map unified status to the legacy stats structure expected by the UI
            setStats({
                icu: { free: data.counts.icu_free },
                general: { free: data.counts.general_free },
                waiting: {
                    icu: data.queue.icu.length,
                    general: data.queue.general.length
                }
            });
            setBeds(data.beds);
            setQueue([...data.queue.icu, ...data.queue.general]);
            setAmbulances(data.ambulances);
            
            // Auto-generate alerts based on state
            const newAlerts = [];
            if (data.counts.icu_free === 0 && data.queue.icu.length > 0) {
                newAlerts.push({ type: "error", message: "No ICU bed available - Critical patients in queue!" });
            }
            data.ambulances.forEach(amb => {
                if (amb.status === "busy") {
                    newAlerts.push({ type: "warning", message: `Ambulance ${amb.id} dispatched for ${amb.patient_detail?.name || 'Critical Patient'}.` });
                }
            });
            setAlerts(newAlerts);

        } catch (err) {
            console.error("Failed to fetch bed data:", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000); 
        return () => clearInterval(interval);
    }, [fetchData]);

    const handleDischarge = async (encounterId) => {
        try {
            await BedAPI.discharge(encounterId);
            fetchData();
        } catch (err) {
            alert("Discharge failed: " + (err.response?.data?.errors || err.message));
        }
    };

    const handleSeed = async () => {
        try {
            await BedAPI.seed();
            fetchData();
        } catch (err) {
            alert("Seed failed");
        }
    };

    if (loading && !stats) return (
        <div className="flex h-screen items-center justify-center bg-gray-50">
            <div className="flex flex-col items-center gap-4">
                <RefreshCw className="h-12 w-12 animate-spin text-blue-600" />
                <span className="text-sm font-bold uppercase tracking-widest text-gray-500">Syncing Bed Grid...</span>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-[#F8FAFC] p-8 animate-in fade-in duration-700">
            {/* Header */}
            <div className="mb-10 flex flex-col justify-between gap-6 md:flex-row md:items-center">
                <div>
                    <h1 className="flex items-center gap-3 text-4xl font-black tracking-tight text-gray-900">
                        <BedIcon className="h-10 w-10 text-blue-600" /> Bed Management
                    </h1>
                    <p className="mt-2 text-lg font-medium text-gray-500">Real-time hospital resource coordination & triage</p>
                </div>
                <div className="flex items-center gap-3">
                    <button 
                        onClick={handleSeed}
                        className="rounded-2xl border border-gray-200 bg-white px-6 py-3 text-sm font-bold text-gray-600 shadow-sm transition-all hover:bg-gray-50 active:scale-95"
                    >
                        Seed Resources
                    </button>
                    <button 
                        onClick={fetchData}
                        className="flex items-center gap-2 rounded-2xl bg-blue-600 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-blue-600/20 transition-all hover:bg-blue-700 active:scale-95"
                    >
                        <RefreshCw size={18} /> Refresh Live
                    </button>
                </div>
            </div>

            {/* Alerts Section */}
            {alerts.length > 0 && (
                <div className="mb-10 flex flex-col gap-3">
                    {alerts.map((alert, i) => (
                        <div key={i} className={`flex items-center gap-4 rounded-3xl border p-5 shadow-sm animate-in slide-in-from-top duration-500 ${
                            alert.type === 'error' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-amber-200 bg-amber-50 text-amber-800'
                        }`}>
                            <AlertCircle size={24} />
                            <span className="font-bold tracking-tight">{alert.message}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Stats Overview */}
            <div className="mb-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard label="Total Capacity" value={stats.total_beds} sub={`Beds Registered`} icon={<BedIcon className="text-blue-600" />} />
                <StatCard label="Available Beds" value={stats.free_beds} sub={`${stats.occupied_beds} Occupied`} color="emerald" icon={<CheckCircle className="text-emerald-600" />} />
                <StatCard label="ICU Status" value={`${stats.icu.free}/${stats.icu.total}`} sub={`${stats.waiting.icu} in queue`} color="rose" icon={<Activity className="text-rose-600" />} />
                <StatCard label="Ambulance Fleet" value={`${stats.ambulance.available}/${stats.ambulance.total}`} sub={`Fleet Ready`} color="amber" icon={<Truck className="text-amber-600" />} />
            </div>

            <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
                {/* Bed Grid */}
                <div className="lg:col-span-8">
                    <div className="mb-6 flex items-center justify-between">
                        <h2 className="text-xl font-black uppercase tracking-widest text-gray-900">Hospital Bed Grid</h2>
                        <div className="flex gap-4">
                            <span className="flex items-center gap-2 text-xs font-bold text-gray-500"><div className="h-3 w-3 rounded-full bg-emerald-500" /> Free</span>
                            <span className="flex items-center gap-2 text-xs font-bold text-gray-500"><div className="h-3 w-3 rounded-full bg-rose-500" /> Occupied</span>
                        </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
                        {beds.map(bed => (
                            <BedTile 
                                key={bed.id} 
                                bed={bed} 
                                onDischarge={handleDischarge} 
                                onHandoff={setHandoffEnc}
                            />
                        ))}
                    </div>
                </div>

                {/* Sidebars: Queues and Ambulances */}
                <div className="flex flex-col gap-10 lg:col-span-4">
                    {/* Waiting Queue */}
                    <div className="rounded-[2.5rem] border border-white bg-white/70 p-8 shadow-2xl shadow-blue-900/5 backdrop-blur-xl">
                        <h3 className="mb-6 flex items-center gap-3 text-lg font-black text-gray-900">
                            <Clock className="text-blue-600" /> Waiting Queue
                        </h3>
                        {queue.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-10 opacity-30">
                                <LogOut size={40} />
                                <p className="mt-2 font-bold uppercase tracking-widest text-sm">No Patients Waiting</p>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-4">
                                {queue.map(q => (
                                    <QueueItem key={q.id} q={q} />
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Ambulance Fleet */}
                    <div className="rounded-[2.5rem] border border-white bg-white/70 p-8 shadow-2xl shadow-blue-900/5 backdrop-blur-xl">
                        <h3 className="mb-6 flex items-center gap-3 text-lg font-black text-gray-900">
                            <Truck className="text-amber-600" /> Ambulance Fleet
                        </h3>
                        <div className="flex flex-col gap-4">
                            {ambulances.map(amb => (
                                <AmbulanceItem key={amb.id} amb={amb} />
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {handoffEnc && (
                <HandoffModal 
                    encounterId={handoffEnc.id} 
                    patientName={handoffEnc.patient_detail?.name} 
                    onClose={() => setHandoffEnc(null)} 
                />
            )}
        </div>
    );
}

function StatCard({ label, value, sub, icon, color = "blue" }) {
    const colors = {
        blue: "border-blue-100 bg-blue-50/50 text-blue-900 shadow-blue-900/5",
        emerald: "border-emerald-100 bg-emerald-50/50 text-emerald-900 shadow-emerald-900/5",
        rose: "border-rose-100 bg-rose-50/50 text-rose-900 shadow-rose-900/5",
        amber: "border-amber-100 bg-amber-50/50 text-amber-900 shadow-amber-900/5",
    };

    return (
        <div className={`rounded-[2rem] border-2 p-6 transition-all hover:scale-105 ${colors[color]}`}>
            <div className="mb-4 flex items-center justify-between">
                <div className="rounded-2xl bg-white p-3 shadow-inner">
                    {icon}
                </div>
                <div className="text-sm font-black uppercase tracking-widest opacity-60">{label}</div>
            </div>
            <div className="text-4xl font-black tracking-tight">{value}</div>
            <div className="mt-1 text-sm font-bold opacity-60">{sub}</div>
        </div>
    );
}

function BedTile({ bed, onDischarge, onHandoff }) {
    const isOccupied = bed.status === "occupied";
    
    return (
        <div className={`group relative flex flex-col items-center justify-center rounded-3xl border-2 p-5 transition-all ${
            isOccupied 
            ? "border-rose-100 bg-white shadow-xl shadow-rose-900/5" 
            : "border-emerald-100 bg-white shadow-xl shadow-emerald-900/5 hover:border-emerald-300"
        }`}>
            <div className={`absolute -right-1 -top-1 h-5 w-5 rounded-full border-4 border-white ${isOccupied ? 'bg-rose-500' : 'bg-emerald-500'}`} />
            
            <div className="mb-3 text-sm font-black text-gray-400 group-hover:text-blue-600">{bed.id}</div>
            
            <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-50 text-xl ${isOccupied ? 'text-rose-500' : 'text-emerald-500'}`}>
                {isOccupied ? <User /> : <BedIcon />}
            </div>
            
            <div className="mt-3 text-[10px] font-black uppercase tracking-widest text-gray-400">{bed.type}</div>
            
            {isOccupied && (
                <div className="mt-4 flex flex-col items-center">
                    <div className="mt-4 flex flex-col items-center gap-2">
                        <span className="mb-1 text-xs font-bold text-gray-800">{bed.patient_detail?.name}</span>
                        <div className="flex gap-2">
                            <button 
                                onClick={() => onDischarge(bed.current_encounter)}
                                className="rounded-xl bg-gray-900 px-3 py-1.5 text-[10px] font-black text-white transition-all hover:bg-rose-600 active:scale-95"
                            >
                                DISCHARGE
                            </button>
                            <button 
                                onClick={() => bed.current_encounter_detail ? onHandoff(bed.current_encounter_detail) : alert("No encounter details available")}
                                className="rounded-xl bg-blue-600 px-3 py-1.5 text-[10px] font-black text-white transition-all hover:bg-blue-700 active:scale-95 flex items-center gap-1"
                                title="Handoff Summary"
                            >
                                <ClipboardList size={12} />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function QueueItem({ q }) {
    const isCritical = q.type === "ICU";
    
    return (
        <div className={`flex items-center gap-4 rounded-2xl border p-4 transition-all hover:translate-x-1 ${
            isCritical ? 'border-rose-100 bg-rose-50/50' : 'border-blue-100 bg-blue-50/50'
        }`}>
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white shadow-sm ${
                isCritical ? 'text-rose-600' : 'text-blue-600'
            }`}>
                <User size={18} />
            </div>
            <div className="flex-1 overflow-hidden">
                <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-bold text-gray-900">{q.patient_detail?.name}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[8px] font-black uppercase tracking-widest ${
                        isCritical ? 'bg-rose-600 text-white' : 'bg-blue-600 text-white'
                    }`}>{q.type}</span>
                </div>
                <div className="mt-0.5 text-[10px] font-bold text-gray-500">Wait Time: {new Date(q.created_at).toLocaleTimeString()}</div>
            </div>
            <div className="text-gray-300"><ChevronRight size={16} /></div>
        </div>
    );
}

function AmbulanceItem({ amb }) {
    const isBusy = amb.status === "busy";
    
    return (
        <div className={`flex items-center gap-4 rounded-2xl border p-4 ${
            isBusy ? 'border-amber-200 bg-amber-50/50 shadow-inner' : 'border-gray-100 bg-gray-50/50'
        }`}>
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white shadow-sm ${
                isBusy ? 'text-amber-600 animate-pulse' : 'text-gray-400'
            }`}>
                <Truck size={18} />
            </div>
            <div className="flex-1">
                <div className="text-xs font-black uppercase tracking-widest text-gray-400">{amb.id}</div>
                <div className={`text-xs font-bold ${isBusy ? 'text-amber-700' : 'text-gray-500'}`}>
                    {isBusy ? `Dispatching ${amb.patient_detail?.name || 'Patient'}` : 'Fleet Ready'}
                </div>
            </div>
            {isBusy && <div className="h-2 w-2 rounded-full bg-amber-500 animate-ping" />}
        </div>
    );
}

