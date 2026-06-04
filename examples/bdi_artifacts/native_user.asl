!start.

+!start <-
    .print("Agent started.");
    .print("Invoking 'unlock' operation directly...");
    .unlock;
    .print("Operation invoked.").

+status(State) <-
    .print("Observed door status change:", State).
