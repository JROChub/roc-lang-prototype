module main

fn main() {
  let a = true;
  let b = false;

  if a && !b {
    print("logic ok");
  } else if a || b {
    print("fallback");
  } else {
    print("nope");
  };
}
