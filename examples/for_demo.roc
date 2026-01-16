module main

fn main() {
  let sum = 0;
  for i in 1..=9 by 2 {
    if i == 3 {
      continue;
    } else {
      set sum = sum + i;
    };
    if i == 9 { break; } else { 0; };
  }
  print("sum is " + sum);
}
