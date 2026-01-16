module main

fn main() {
  print("=== Roc: The First Program ===");

  let a = 40;
  let b = 2;
  let result = a + b;

  print("Result is " + result);

  if result == 42 {
    print("Everything feels right.");
  } else {
    print("Something is off.");
  };
}
