!start.

+!start <-
    .print("Agent started.");
    .print("Invoking 'unlock' operation directly with key...");
    .unlock("master_key_123");
    .print("Operation invoked.").

+status(State) <-
    .print("Observed door status change:", State).
