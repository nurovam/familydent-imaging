import { useEffect, useRef, type ReactNode } from 'react';

/** Native modal supplies focus containment, Escape and return-to-trigger semantics. */
export function TaskDialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    return () => { dialog.close(); trigger?.focus({ preventScroll: true }); };
  }, []);
  return <dialog ref={ref} className="task-dialog clinical-workspace" aria-label={title} onCancel={event => { event.preventDefault(); onClose(); }}>
    <div className="dialog-actions"><button className="btn" type="button" onClick={onClose} aria-label="Закрыть форму">Закрыть</button></div>
    {children}
  </dialog>;
}
