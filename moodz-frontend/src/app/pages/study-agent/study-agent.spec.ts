import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyAgent } from './study-agent';

describe('StudyAgent', () => {
  let component: StudyAgent;
  let fixture: ComponentFixture<StudyAgent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StudyAgent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(StudyAgent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
