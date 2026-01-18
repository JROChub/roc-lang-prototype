module module_demo

import math_utils;

enum Mode { Add, Twice }

fn main() {
  let mode = Add;
  let result = match mode {
    Add => { add(2, 5); }
    Twice => { twice(4); }
  };
  print("result is " + result);
}
