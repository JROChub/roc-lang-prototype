enum Color { Red }

fn main() {
  let c = Red;
  let label = match c {
    Blue => { "b"; }
    _ => { "r"; }
  };
  print(label);
}
