module main

fn main() {
  let n = 3;
  let label = match n {
    1 => { "one"; }
    2 => { "two"; }
    _ => { "other"; }
  };
  print("label is " + label);
}
