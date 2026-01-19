module main

enum Option { None, Some(Int) }

fn main() {
  let value = Some(5);
  let msg = match value {
    Some(x) => { "value is " + x; }
    _ => { "value is none"; }
  };
  print(msg);
}
