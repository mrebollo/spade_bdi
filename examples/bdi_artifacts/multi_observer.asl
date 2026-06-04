!start.

+!start <-
    .print("Multi Observer started").

+measure(Temp, Unidad, Estado) <-
    .print("measure -> Temp:", Temp, ", Unidad:", Unidad, ", Estado:", Estado).

+status(State) <-
    .print("status -> State:", State).

+battery(Level) <-
    .print("battery -> Level:", Level).

+sensor_data(Val1, Val2, Val3) <-
    .print("sensor_data -> Val1:", Val1, ", Val2:", Val2, ", Val3:", Val3).
