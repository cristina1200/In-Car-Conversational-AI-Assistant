import { useEffect, useState } from "react";

export function useAnimatedNumber(
  targetValue: number,
  duration = 600
) {
  const [displayValue, setDisplayValue] =
    useState(targetValue);

  useEffect(() => {
    const startValue = displayValue;
    const difference = targetValue - startValue;

    if (difference === 0) {
      return;
    }

    const startTime = performance.now();

    function animate(currentTime: number) {
      const elapsed = currentTime - startTime;

      const progress = Math.min(
        elapsed / duration,
        1
      );

      const nextValue =
        startValue + difference * progress;

      setDisplayValue(Math.round(nextValue));

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    }

    requestAnimationFrame(animate);
  }, [targetValue]);

  return displayValue;
}