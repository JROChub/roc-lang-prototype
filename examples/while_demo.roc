module main

fn main() {
  let i = 0;
  while true {
    set i = i + 1;
    if i == 2 { continue; } else { 0; };
    print("i = " + i);
    if i >= 4 { break; } else { 0; };
  }
}
