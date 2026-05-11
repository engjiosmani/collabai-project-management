import {
    Cell,
    Legend,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
} from "recharts";

const COLORS = ["#22c55e", "#f97316"];

function CompletionChart({ completed, pending, total }) {
    const data = [
        { name: "Completed", value: completed },
        { name: "Pending", value: pending },
    ];

    return (
        <div className="dashboard-chart-wrap">
            <div className="dashboard-chart-summary">
                <div>
                    <p className="dashboard-empty-kicker">Task status</p>
                    <h3>{total} total tasks</h3>
                </div>
                <p className="dashboard-chart-percentage">{total ? Math.round((completed / total) * 100) : 0}% done</p>
            </div>

            <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                    <Pie
                        data={data}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={72}
                        outerRadius={104}
                        paddingAngle={3}
                        stroke="none"
                    >
                        {data.map((entry, index) => (
                            <Cell key={`cell-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip />
                    <Legend verticalAlign="bottom" height={32} />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
}

export default CompletionChart;

