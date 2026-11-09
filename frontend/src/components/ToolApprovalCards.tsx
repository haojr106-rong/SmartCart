import type { ToolApproval } from "../types";
import "./confirmations.css";

const labels: Record<string,string> = { statement: "偏好内容", previous_statement: "原偏好", kind: "偏好类型" };
function details(item: ToolApproval) {
  try {
    const args = typeof item.arguments === "string" ? JSON.parse(item.arguments) : item.arguments;
    if (item.tool === "activate_preferences_tool") {
      const statements: string[] = Array.isArray(args.statements) ? args.statements.map(String) : [];
      return statements.length
        ? <div><strong>本轮准备使用：</strong><ul>{statements.map((value,index) => <li key={index}>{value}</li>)}</ul></div>
        : <p>偏好候选无法展示，请拒绝后重试。</p>;
    }
    return Object.entries(args).filter(([key]) => key in labels).map(([key,value]) =>
      <p key={key}><strong>{labels[key]}：</strong>{key === "kind" ? (value === "dislike" ? "避免" : "喜欢") : String(value)}</p>);
  } catch { return <p>参数无法展示，请拒绝后重新描述需求。</p>; }
}
export function ToolApprovalCards({items,busy,onResolve}:{items:ToolApproval[];busy:boolean;onResolve:(id:string,approved:boolean)=>Promise<void>}) {
  if (!items.length) return null;
  return <section className="confirmation-list confirmations-section" aria-label="待确认的偏好操作">
    {items.map(item => <article className="confirmation-card" key={item.id}>
      <h3>{item.label}</h3>
      {details(item)}
      <p>{item.tool === "activate_preferences_tool"
        ? "批准后仅在本轮商品检索或推荐中使用，不会修改长期偏好；拒绝后按本轮原始要求继续。"
        : "批准后执行本次操作。保存时会提炼稳定购物偏好；拒绝不会修改记忆。"}</p>
      <div className="confirmation-actions">
        <button className="confirmation-secondary" type="button" disabled={busy} onClick={() => void onResolve(item.id,false)}>拒绝</button>
        <button className="confirmation-primary" type="button" disabled={busy} onClick={() => void onResolve(item.id,true)}>{item.tool === "activate_preferences_tool" ? "本轮使用这些偏好" : "批准本次操作"}</button>
      </div>
    </article>)}
  </section>;
}
