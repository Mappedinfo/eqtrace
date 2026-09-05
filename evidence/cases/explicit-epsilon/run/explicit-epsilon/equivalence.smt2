; benchmark generated from python API
(set-info :status unknown)
(declare-fun x () Real)
(declare-fun mu () Real)
(declare-fun sigma () Real)
(declare-fun epsilon () Real)
(assert
 (<= (- 2.0) x))
(assert
 (>= 2.0 x))
(assert
 (<= (- 1.0) mu))
(assert
 (>= 1.0 mu))
(assert
 (<= 1.0 sigma))
(assert
 (>= 3.0 sigma))
(assert
 (<= (/ 1.0 100.0) epsilon))
(assert
 (>= (/ 1.0 10.0) epsilon))
(assert
 (let ((?x12 (+ sigma epsilon)))
(let ((?x24 (/ (- x mu) ?x12)))
(and (distinct ?x24 ?x24) true))))
(check-sat)
