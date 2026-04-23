import { useState, useEffect } from "react";
import { 
    X, 
    ClipboardList, 
    History, 
    AlertTriangle, 
    CheckCircle, 
    Copy, 
    Download,
    Activity,
    Clock
} from "lucide-react";
import { BedAPI } from "../api/client";

export default function HandoffModal({ encounterId, patientName, onClose }) {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedSummary, setSelectedSummary] = useState(null);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const data = await BedAPI.getHandoffHistory(encounterId);
                // API returns a plain array directly
                const list = Array.isArray(data) ? data : (data?.history || []);
                setHistory(list);
                if (list.length > 0) {
                    setSelectedSummary(list[0]);
                }
            } catch (err) {
                console.error("Failed to fetch handoff history:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, [encounterId]);

    const handleCopy = () => {
        if (!selectedSummary) return;
        navigator.clipboard.writeText(selectedSummary.summary_text);
        alert("Summary copied to clipboard!");
    };

    const handleDownload = () => {
        if (!selectedSummary) return;
        const element = document.createElement("a");
        const file = new Blob([selectedSummary.summary_text], { type: 'text/plain' });
        element.href = URL.createObjectURL(file);
        element.download = `Handoff_${patientName}_${new Date(selectedSummary.created_at).toLocaleDateString()}.txt`;
        document.body.appendChild(element);
        element.click();
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content" style={{ width: "800px", maxWidth: "95vw", padding: 0, overflow: "hidden", borderRadius: 24 }}>
                <div style={{ display: "flex", height: "600px" }}>
                    
                    {/* Sidebar: History */}
                    <div style={{ width: "260px", borderRight: "1px solid var(--border)", background: "var(--surface2)", display: "flex", flexDirection: "column" }}>
                        <div style={{ padding: "1.5rem", borderBottom: "1px solid var(--border)" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.25rem" }}>
                                <History size={18} style={{ color: "var(--indigo)" }} />
                                <span style={{ fontWeight: 900, fontSize: "0.85rem", letterSpacing: "0.05em" }}>HISTORY</span>
                            </div>
                            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: 600 }}>Previous Shift Reports</div>
                        </div>
                        <div style={{ flex: 1, overflowY: "auto", padding: "0.75rem" }}>
                            {loading ? (
                                <div style={{ padding: "1rem", textAlign: "center", opacity: 0.5 }}><div className="spinner" style={{ margin: "0 auto 0.5rem" }} /> Loading...</div>
                            ) : history.length === 0 ? (
                                <div style={{ padding: "1rem", textAlign: "center", opacity: 0.4, fontSize: "0.8rem" }}>No history found</div>
                            ) : (
                                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                                    {history.map((h, idx) => (
                                        <div 
                                            key={h.id}
                                            onClick={() => setSelectedSummary(h)}
                                            style={{
                                                padding: "0.85rem",
                                                borderRadius: 12,
                                                cursor: "pointer",
                                                background: selectedSummary?.id === h.id ? "white" : "transparent",
                                                border: `1px solid ${selectedSummary?.id === h.id ? "var(--indigo)" : "transparent"}`,
                                                boxShadow: selectedSummary?.id === h.id ? "0 4px 12px rgba(99,102,241,0.1)" : "none",
                                                transition: "all 0.2s"
                                            }}
                                        >
                                            <div style={{ fontWeight: 800, fontSize: "0.8rem", color: selectedSummary?.id === h.id ? "var(--indigo)" : "var(--text)" }}>
                                                {idx === 0 ? "Latest Summary" : `Shift Report #${history.length - idx}`}
                                            </div>
                                            <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", marginTop: 4 }}>
                                                {new Date(h.created_at).toLocaleString()}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Main Content */}
                    <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "white" }}>
                        <div style={{ padding: "1.5rem", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div>
                                <div style={{ fontSize: "0.7rem", fontWeight: 800, color: "var(--indigo)", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 2 }}>Patient Handoff</div>
                                <div style={{ fontSize: "1.25rem", fontWeight: 900 }}>{patientName}</div>
                            </div>
                            <button className="btn-close" onClick={onClose}><X size={20} /></button>
                        </div>

                        <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>
                            {selectedSummary ? (
                                <div>
                                    {/* Risks Section */}
                                    {selectedSummary.risks_json?.length > 0 && (
                                        <div style={{ marginBottom: "1.5rem" }}>
                                            <div style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--text-muted)", marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                                <AlertTriangle size={14} style={{ color: "#ef4444" }} /> CLINICAL RISKS & ALERTS
                                            </div>
                                            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                                                {selectedSummary.risks_json.map((risk, i) => (
                                                    <div key={i} style={{ 
                                                        padding: "0.5rem 0.85rem", 
                                                        borderRadius: 10, 
                                                        fontSize: "0.75rem", 
                                                        fontWeight: 700,
                                                        background: risk.severity === 'high' ? 'rgba(239,68,68,0.1)' : risk.severity === 'medium' ? 'rgba(245,158,11,0.1)' : 'rgba(16,185,129,0.1)',
                                                        color: risk.severity === 'high' ? '#ef4444' : risk.severity === 'medium' ? '#f59e0b' : '#10b981',
                                                        border: `1px solid ${risk.severity === 'high' ? 'rgba(239,68,68,0.2)' : risk.severity === 'medium' ? 'rgba(245,158,11,0.2)' : 'rgba(16,185,129,0.2)'}`
                                                    }}>
                                                        {risk.severity === 'high' ? '🚨' : risk.severity === 'medium' ? '⚠️' : '✅'} {risk.type}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Summary Text */}
                                    <div style={{ background: "var(--surface2)", padding: "1.5rem", borderRadius: 16, border: "1px solid var(--border)" }}>
                                        <div style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--text-muted)", marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                            <ClipboardList size={14} /> CLINICAL SUMMARY
                                        </div>
                                        <div style={{ 
                                            fontSize: "0.95rem", 
                                            lineHeight: 1.6, 
                                            color: "var(--text)", 
                                            whiteSpace: "pre-wrap", 
                                            fontWeight: 500,
                                            fontFamily: "Inter, system-ui, sans-serif"
                                        }}>
                                            {selectedSummary.summary_text}
                                        </div>
                                    </div>
                                </div>
                            ) : !loading && (
                                <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", opacity: 0.5 }}>
                                    <ClipboardList size={48} />
                                    <div style={{ marginTop: "1rem", fontWeight: 700 }}>No summary available for this encounter.</div>
                                </div>
                            )}
                        </div>

                        {/* Footer Actions */}
                        <div style={{ padding: "1.25rem 1.5rem", borderTop: "1px solid var(--border)", display: "flex", gap: "1rem" }}>
                            <button 
                                className="btn btn-ghost" 
                                style={{ flex: 1, height: "48px", gap: "0.5rem" }}
                                onClick={handleCopy}
                                disabled={!selectedSummary}
                            >
                                <Copy size={18} /> Copy to Clipboard
                            </button>
                            <button 
                                className="btn btn-indigo" 
                                style={{ flex: 1, height: "48px", gap: "0.5rem" }}
                                onClick={handleDownload}
                                disabled={!selectedSummary}
                            >
                                <Download size={18} /> Download .txt
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
