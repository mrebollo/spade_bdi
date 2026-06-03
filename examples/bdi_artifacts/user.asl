!start.

+!start <-
    .print("Agent started.");
    .print("Invoking 'unlock' operation on door...");
    .use("door@localhost", "unlock");
    .print("Operation invoked.").

+status(State) <-
    .print("Observed door status change:", State).
