import {
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Button, ErrorBox, Field, Sheet } from "./ui";
import { Picker } from "./reference";
import {
  fromDisplay,
  toDisplay,
  rounded,
  validPersonalNumber,
  type PersonalField,
  type PersonalUnit,
} from "../personalData";

const rowHeight = 44;
// Scrolling selects the centered row; a click is not required after dragging.
function NumberWheel({
  label,
  value,
  values,
  onChange,
}: {
  label: string;
  value: number;
  values: number[];
  onChange: (value: number) => void;
}) {
  const list = useRef<HTMLDivElement>(null),
    timer = useRef<ReturnType<typeof setTimeout> | null>(null),
    scrolling = useRef(false),
    emitted = useRef<number | null>(null);
  const id = useId(),
    index = Math.max(0, values.indexOf(value));
  useLayoutEffect(() => {
    const align = () => {
      if (scrolling.current && emitted.current === value) return;
      if (list.current?.clientHeight)
        list.current.scrollTop = index * rowHeight;
    };
    align();
    // A dialog has no layout until showModal(); align again once it becomes visible.
    const frame = requestAnimationFrame(align);
    const observer = new ResizeObserver(align);
    if (list.current) observer.observe(list.current);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [index, value]);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );
  const choose = (next: number) => {
    scrolling.current = false;
    emitted.current = next;
    if (timer.current) clearTimeout(timer.current);
    onChange(next);
    if (list.current)
      list.current.scrollTop = Math.max(0, values.indexOf(next)) * rowHeight;
  };
  return (
    <div
      ref={list}
      className="number-wheel"
      role="listbox"
      aria-label={label}
      aria-activedescendant={id + "-" + index}
      tabIndex={0}
      onKeyDown={(e) => {
        let next = index;
        if (e.key === "ArrowDown")
          next = Math.min(values.length - 1, index + 1);
        else if (e.key === "ArrowUp") next = Math.max(0, index - 1);
        else if (e.key === "Home") next = 0;
        else if (e.key === "End") next = values.length - 1;
        else return;
        e.preventDefault();
        choose(values[next]);
      }}
      onScroll={(e) => {
        const next =
          values[
            Math.max(
              0,
              Math.min(
                values.length - 1,
                Math.round(e.currentTarget.scrollTop / rowHeight),
              ),
            )
          ];
        if (next === value) return;
        scrolling.current = true;
        emitted.current = next;
        onChange(next);
        if (timer.current) clearTimeout(timer.current);
        timer.current = setTimeout(() => {
          scrolling.current = false;
        }, 140);
      }}
    >
      <div className="number-wheel-space" aria-hidden="true" />
      {values.map((n, i) => (
        <button
          type="button"
          key={n}
          id={id + "-" + i}
          role="option"
          tabIndex={-1}
          aria-selected={value === n}
          className={value === n ? "chosen" : ""}
          onClick={() => choose(n)}
        >
          {n}
        </button>
      ))}
      <div className="number-wheel-space" aria-hidden="true" />
    </div>
  );
}

export function PersonalDataPicker({
  field,
  value,
  initialUnit,
  onSave,
  onClose,
}: {
  field: PersonalField;
  value: string | number | null;
  initialUnit?: PersonalUnit;
  onSave: (value: string | number, unit?: PersonalUnit) => void | Promise<void>;
  onClose: () => void;
}) {
  const title = {
    sex: "Sexo",
    age: "Edad",
    height: "Altura",
    weight: "Peso",
    target_weight: "Peso objetivo",
    speed: "Velocidad",
  }[field];
  const defaultValue = field === "age" ? 20 : field === "height" ? 170 : 60;
  const [unit, setUnit] = useState<PersonalUnit>(
    initialUnit ??
      (field === "height" ? "cm" : field === "age" ? "años" : "kg"),
  );
  const [canonical, setCanonical] = useState(
    typeof value === "number" ? value : defaultValue,
  );
  const [raw, setRaw] = useState(
    String(
      rounded(
        toDisplay(typeof value === "number" ? value : defaultValue, unit),
      ),
    ),
  );
  const [feet, setFeet] = useState(
      String(Math.floor(toDisplay(canonical, "ft/in") / 12)),
    ),
    [inches, setInches] = useState(
      String(rounded(toDisplay(canonical, "ft/in") % 12)),
    );
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const display = toDisplay(canonical, unit),
    safeDisplay = Number.isFinite(display) && display >= 0 ? display : 0,
    whole = Math.floor(safeDisplay),
    fraction = Math.min(9, Math.floor((safeDisplay - whole) * 10 + 1e-6));
  const wheelValue = unit === "ft/in" ? Math.floor(safeDisplay / 12) : whole;
  const values = useMemo(() => {
    // Keep the wheel small even when a custom value is far outside typical measurements.
    const base = field === "age" ? 150 : unit === "ft/in" ? 12 : 500;
    if (wheelValue <= base)
      return Array.from({ length: base + 1 }, (_, i) => i);
    return Array.from(
      { length: 101 },
      (_, i) => Math.max(0, wheelValue - 50) + i,
    );
  }, [
    field,
    unit,
    wheelValue > 500 ||
    (unit === "ft/in" && wheelValue > 12) ||
    (field === "age" && wheelValue > 150)
      ? wheelValue
      : 0,
  ]);
  const change = (n: number) => {
    const next = fromDisplay(n, unit);
    setCanonical(next);
    setRaw(String(rounded(n)));
    if (unit === "ft/in") {
      setFeet(String(Math.floor(n / 12)));
      setInches(String(rounded(n % 12)));
    }
    setError("");
  };
  const switchUnit = (next: PersonalUnit) => {
    setUnit(next);
    setRaw(String(rounded(toDisplay(canonical, next))));
    if (next === "ft/in") {
      setFeet(String(Math.floor(toDisplay(canonical, next) / 12)));
      setInches(String(rounded(toDisplay(canonical, next) % 12)));
    }
    setError("");
  };
  const valid =
    Number.isFinite(display) &&
    validPersonalNumber(field, canonical) &&
    (unit === "ft/in"
      ? feet !== "" && inches !== "" && Number(feet) >= 0 && Number(inches) >= 0
      : raw.trim() !== "" && Number.isFinite(Number(raw)));
  if (field === "sex" || field === "speed")
    return (
      <Picker
        title={title}
        value={value ?? ""}
        choices={
          field === "sex"
            ? ["Hombre", "Mujer", "Prefiero no decir"]
            : ["Recomendado", "Lento"]
        }
        onSave={onSave}
        onClose={onClose}
      />
    );
  return (
    <Sheet
      title={title}
      className={"personal-picker " + (field === "age" ? "age-picker" : "")}
      onClose={() => !busy && onClose()}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (!valid) {
            setError(
              field === "age"
                ? "Introduce una edad entera de cero años en adelante."
                : "Introduce un valor numérico mayor que cero.",
            );
            return;
          }
          setBusy(true);
          setError("");
          try {
            await onSave(canonical, unit);
            onClose();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {field !== "age" && (
          <div className="personal-unit-tabs">
            {(field === "height" ? ["cm", "ft/in"] : ["kg", "lb"]).map((v) => (
              <button
                key={v}
                type="button"
                aria-pressed={unit === v}
                className={unit === v ? "selected" : ""}
                onClick={() => switchUnit(v as PersonalUnit)}
              >
                {v === "lb" ? "lbs" : v}
              </button>
            ))}
          </div>
        )}
        <div className="personal-wheels">
          <div className="personal-wheel-highlight" />
          <NumberWheel
            label={unit === "ft/in" ? "Pies" : title}
            value={wheelValue}
            values={values}
            onChange={(n) =>
              change(
                unit === "ft/in"
                  ? n * 12 + (display % 12)
                  : field === "age" || field === "height"
                    ? n
                    : n + (display - whole),
              )
            }
          />
          {(field === "weight" || field === "target_weight") &&
            unit !== "ft/in" && (
              <>
                <span className="wheel-dot">.</span>
                <NumberWheel
                  label={"Decimales de " + title.toLowerCase()}
                  value={fraction}
                  values={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
                  onChange={(n) => change(whole + n / 10)}
                />
              </>
            )}
          {unit === "ft/in" && (
            <>
              <span className="wheel-unit">ft</span>
              <NumberWheel
                label="Pulgadas"
                value={Math.floor(display % 12)}
                values={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
                onChange={(n) => change(Math.floor(display / 12) * 12 + n)}
              />
            </>
          )}
          <span className="wheel-unit">
            {field === "age" ? "años" : unit === "ft/in" ? "in" : unit}
          </span>
        </div>
        <div className="personal-direct-entry">
          {unit === "ft/in" ? (
            <div className="two-fields">
              <Field label="Pies">
                <input
                  inputMode="decimal"
                  type="number"
                  step="1"
                  value={feet}
                  onChange={(e) => {
                    setFeet(e.target.value);
                    if (
                      e.target.value !== "" &&
                      Number.isFinite(Number(e.target.value))
                    ) {
                      const n = Number(e.target.value) * 12 + Number(inches);
                      setCanonical(fromDisplay(n, unit));
                    }
                    setError("");
                  }}
                />
              </Field>
              <Field label="Pulgadas">
                <input
                  inputMode="decimal"
                  type="number"
                  step="any"
                  value={inches}
                  onChange={(e) => {
                    setInches(e.target.value);
                    if (
                      e.target.value !== "" &&
                      Number.isFinite(Number(e.target.value))
                    ) {
                      const n = Number(feet) * 12 + Number(e.target.value);
                      setCanonical(fromDisplay(n, unit));
                    }
                    setError("");
                  }}
                />
              </Field>
            </div>
          ) : (
            <Field
              label={title + " (" + (field === "age" ? "años" : unit) + ")"}
            >
              <input
                inputMode={field === "age" ? "numeric" : "decimal"}
                type="number"
                step={field === "age" ? "1" : "any"}
                value={raw}
                onChange={(e) => {
                  setRaw(e.target.value);
                  if (
                    e.target.value !== "" &&
                    Number.isFinite(Number(e.target.value))
                  )
                    setCanonical(fromDisplay(Number(e.target.value), unit));
                  setError("");
                }}
              />
            </Field>
          )}
        </div>
        <ErrorBox error={error} />
        <Button busy={busy} disabled={!valid}>
          {field === "weight" || field === "target_weight"
            ? "Guardar"
            : "Aceptar"}
        </Button>
      </form>
    </Sheet>
  );
}
